# grant-large-pages.ps1
#
# ONE-TIME setup so the Llamacpp Model Launcher can start Strata WITHOUT elevation.
#
# Strata uses 2 MB large pages, which need the "Lock pages in memory" right
# (SeLockMemoryPrivilege) plus "Increase a process working set"
# (SeIncreaseWorkingSetPrivilege). The Strata .bat files self-elevate to enable
# them per-run; instead, this script assigns the rights to your Windows account
# once. The launcher then enables them in its own token at launch (no UAC prompt),
# and the Strata engine inherits them.
#
# HOW TO USE:
#   1. Right-click PowerShell -> "Run as administrator", then:
#        powershell -ExecutionPolicy Bypass -File grant-large-pages.ps1
#   2. Log OFF and back ON (the rights land in your logon token at next sign-in).
#   3. Launch Strata from the Llamacpp Model Launcher normally.
#
# To undo:
#        powershell -ExecutionPolicy Bypass -File grant-large-pages.ps1 -Revoke
#
# If you skip this script entirely, Strata still works — it just falls back to
# 4 KB pages (slower), and the launcher logs a warning.

#Requires -RunAsAdministrator
param([switch]$Revoke)

$Rights = @('SeLockMemoryPrivilege', 'SeIncreaseWorkingSetPrivilege')

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class LargePagesRights
{
    [StructLayout(LayoutKind.Sequential)]
    private struct LSA_UNICODE_STRING
    {
        public ushort Length;
        public ushort MaximumLength;
        public IntPtr Buffer;
    }

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode)]
    private static extern int LsaOpenPolicy(IntPtr SystemName, ref LSA_UNICODE_STRING ObjectName,
                                            int AccessMask, out IntPtr PolicyHandle);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode)]
    private static extern int LsaAddAccountRights(IntPtr PolicyHandle, IntPtr AccountSid,
                                                  LSA_UNICODE_STRING[] UserRights, int CountOfRights);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode)]
    private static extern int LsaRemoveAccountRights(IntPtr PolicyHandle, IntPtr AccountSid,
                                                     bool AllRights, LSA_UNICODE_STRING[] UserRights,
                                                     int CountOfRights);

    [DllImport("advapi32.dll")]
    private static extern int LsaClose(IntPtr PolicyHandle);

    [DllImport("advapi32.dll")]
    private static extern int LsaNtStatusToWinError(int NTSTATUS);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertStringSidToSid(string StringSid, out IntPtr Sid);

    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr hMem);

    private static LSA_UNICODE_STRING ToLsaString(string s)
    {
        var bytes = System.Text.Encoding.Unicode.GetBytes(s);
        var buffer = Marshal.AllocHGlobal(bytes.Length);
        Marshal.Copy(bytes, 0, buffer, bytes.Length);
        return new LSA_UNICODE_STRING
        {
            Length = (ushort)bytes.Length,
            MaximumLength = (ushort)(bytes.Length + 2),
            Buffer = buffer
        };
    }

    // Returns 0 on success, otherwise the Win32 error code translated from the NTSTATUS.
    public static int Set(string[] rights, string sidString, bool revoke)
    {
        IntPtr sid;
        if (!ConvertStringSidToSid(sidString, out sid))
            return Marshal.GetLastWin32Error();
        try
        {
            var objectName = new LSA_UNICODE_STRING(); // empty name = local system policy
            IntPtr policy;
            int status = LsaOpenPolicy(IntPtr.Zero, ref objectName, 0x000F0FFF, out policy); // POLICY_ALL_ACCESS
            if (status != 0) return LsaNtStatusToWinError(status);
            try
            {
                var lsaRights = Array.ConvertAll(rights, ToLsaString);
                status = revoke
                    ? LsaRemoveAccountRights(policy, sid, false, lsaRights, lsaRights.Length)
                    : LsaAddAccountRights(policy, sid, lsaRights, lsaRights.Length);
                return status == 0 ? 0 : LsaNtStatusToWinError(status);
            }
            finally
            {
                LsaClose(policy);
            }
        }
        finally
        {
            LocalFree(sid);
        }
    }
}
'@

$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = if ($Revoke) { 'Revoking' } else { 'Granting' }
Write-Host "$action for $account ($sid):" -ForegroundColor Cyan
$Rights | ForEach-Object { Write-Host "  $_" }

$rc = [LargePagesRights]::Set($Rights, $sid, [bool]$Revoke)
if ($rc -eq 0) {
    if ($Revoke) {
        Write-Host "`nDone. Rights removed. Log off/on to take effect." -ForegroundColor Green
    } else {
        Write-Host "`nDone. Now LOG OFF and back ON so the rights enter your logon token." -ForegroundColor Green
        Write-Host "After that, the launcher starts Strata with 2 MB large pages - no UAC prompt." -ForegroundColor Green
    }
} else {
    Write-Host "`nFAILED (Win32 error $rc). Make sure PowerShell is elevated (Run as administrator)." -ForegroundColor Red
    exit $rc
}
