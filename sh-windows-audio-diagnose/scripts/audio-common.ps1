# 共享库：CoreAudio / IPolicyConfig / 测试音
# 用法：在脚本内 . "$PSScriptRoot\audio-common.ps1"（同一 PS 进程内可重复 dot-source）
# 说明：本文件须保持 UTF-8 BOM，否则 PS 5.1 会把中文读成乱码

$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8

if (-not ('AudioKit' -as [type])) {
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential)]
public struct PROPERTYKEY { public Guid fmtid; public int pid; }

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
public class MMDeviceEnumeratorComObject { }

[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator {
    int EnumAudioEndpoints(int dataFlow, int dwStateMask, out IMMDeviceCollection ppDevices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}

[ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceCollection {
    int GetCount(out int pcDevices);
    int Item(int nDevice, out IMMDevice ppDevice);
}

[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice {
    int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
    int OpenPropertyStore(int stgmAccess, out IPropertyStore ppProperties);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string ppstrId);
    int GetState(out int pdwState);
}

[ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPropertyStore {
    int GetCount(out int cProps);
    int GetAt(int iProp, out PROPERTYKEY pkey);
    int GetValue(ref PROPERTYKEY key, out PropVariant pv);
    int SetValue(ref PROPERTYKEY key, ref PropVariant propvar);
    int Commit();
}

[StructLayout(LayoutKind.Explicit)]
public struct PropVariant {
    [FieldOffset(0)] public ushort vt;
    [FieldOffset(8)] public IntPtr pointerValue;
    [FieldOffset(8)] public int intValue;
    [FieldOffset(8)] public float floatValue;
}

[ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioEndpointVolume {
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out int pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetChannelVolumeLevel(uint nChannel, float fLevelDB, Guid pguidEventContext);
    int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, Guid pguidEventContext);
    int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
    int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, Guid pguidEventContext);
    int GetMute(out bool pbMute);
    int GetVolumeStepInfo(out int pnStep, out int pnStepCount);
    int VolumeStepUp(Guid pguidEventContext);
    int VolumeStepDown(Guid pguidEventContext);
    int QueryHardwareSupport(out int pdwHardwareSupportMask);
    int GetVolumeRange(out float pflVolumeMindB, out float pflVolumeMaxdB, out float pflVolumeIncrementdB);
}

[ComImport, Guid("870af99c-171d-4f9e-af0d-e63df40c2bc9")]
public class CPolicyConfigClient { }

[ComImport, Guid("f8679f50-850a-41cf-9c72-430f290290c8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPolicyConfig {
    int GetMixFormat(string pszDeviceName, IntPtr ppFormat);
    int GetDeviceFormat(string pszDeviceName, bool bDefault, IntPtr ppFormat);
    int ResetDeviceFormat(string pszDeviceName);
    int SetDeviceFormat(string pszDeviceName, IntPtr pEndpointFormat, IntPtr mixFormat);
    int GetProcessingPeriod(string pszDeviceName, bool bDefault, IntPtr pmftDefaultPeriod, IntPtr pmftMinimumPeriod);
    int SetProcessingPeriod(string pszDeviceName, IntPtr pmftPeriod);
    int GetShareMode(string pszDeviceName, IntPtr pMode);
    int SetShareMode(string pszDeviceName, IntPtr mode);
    int GetPropertyValue(string pszDeviceName, bool bFxStore, ref PROPERTYKEY key, IntPtr pv);
    int SetPropertyValue(string pszDeviceName, bool bFxStore, ref PROPERTYKEY key, IntPtr pv);
    int SetDefaultEndpoint(string pszDeviceName, int role);
    int SetEndpointVisibility(string pszDeviceName, bool bVisible);
}

public class AudioDevice {
    public string Name = "";
    public string Id = "";
    public int State = 0;
    public string Enumerator = "";
    public string Desc = "";
}

public static class AudioKit {
    private static readonly Guid PKEY_Device_FriendlyName = new Guid("a45c254e-df1c-4efd-8020-67d146a850e0");
    private static readonly Guid IID_IAudioEndpointVolume = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");

    private static string GetPropString(IMMDevice d, Guid fmtid, int pid) {
        IPropertyStore store;
        if (d.OpenPropertyStore(0, out store) != 0) return "";
        var pk = new PROPERTYKEY(); pk.fmtid = fmtid; pk.pid = pid;
        PropVariant pv;
        if (store.GetValue(ref pk, out pv) == 0 && pv.vt == 31) return Marshal.PtrToStringUni(pv.pointerValue);
        return "";
    }

    private static AudioDevice Wrap(IMMDevice d) {
        var ad = new AudioDevice();
        string id; d.GetId(out id); ad.Id = id;
        int st; d.GetState(out st); ad.State = st;
        ad.Name = GetPropString(d, PKEY_Device_FriendlyName, 14);
        ad.Desc = GetPropString(d, PKEY_Device_FriendlyName, 2);
        ad.Enumerator = GetPropString(d, PKEY_Device_FriendlyName, 24);
        return ad;
    }

    public static AudioDevice[] EnumDevices(int flow) { return EnumDevices(flow, 0xF); }

    public static AudioDevice[] EnumDevices(int flow, int dwStateMask) {
        var result = new List<AudioDevice>();
        var en = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDeviceCollection col;
        if (en.EnumAudioEndpoints(flow, dwStateMask, out col) != 0) return result.ToArray();
        int n; col.GetCount(out n);
        for (int i = 0; i < n; i++) {
            IMMDevice d; col.Item(i, out d);
            result.Add(Wrap(d));
        }
        return result.ToArray();
    }

    public static AudioDevice GetDefault(int flow, int role) {
        var en = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice d;
        if (en.GetDefaultAudioEndpoint(flow, role, out d) != 0) return null;
        return Wrap(d);
    }

    public static int SetDefault(string deviceId, int role) {
        var pc = (IPolicyConfig)(new CPolicyConfigClient());
        return pc.SetDefaultEndpoint(deviceId, role);
    }

    public static string VolumeInfo() {
        var en = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice d;
        if (en.GetDefaultAudioEndpoint(0, 0, out d) != 0) return "n/a";
        object o;
        var iid = IID_IAudioEndpointVolume;
        if (d.Activate(ref iid, 1, IntPtr.Zero, out o) != 0) return "n/a";
        var epv = o as IAudioEndpointVolume;
        if (epv == null) return "n/a";
        float f; bool m;
        epv.GetMasterVolumeLevelScalar(out f);
        epv.GetMute(out m);
        return Math.Round(f * 100) + "%" + (m ? " [已静音]" : "");
    }

    public static string SetVolume(float scalar, bool mute) {
        var en = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice d;
        if (en.GetDefaultAudioEndpoint(0, 0, out d) != 0) return "no default device";
        object o;
        var iid = IID_IAudioEndpointVolume;
        if (d.Activate(ref iid, 1, IntPtr.Zero, out o) != 0) return "activate failed";
        var epv = o as IAudioEndpointVolume;
        if (epv == null) return "no IAudioEndpointVolume";
        epv.SetMute(mute, Guid.Empty);
        int hr = epv.SetMasterVolumeLevelScalar(scalar, Guid.Empty);
        return "volume=" + Math.Round(scalar * 100) + "% mute=" + mute + " hr=0x" + hr.ToString("X8");
    }

    private static double Envelope(int i, int n, int rate) {
        int fade = rate / 50;
        double f = 1.0;
        if (i < fade) f = (double)i / fade;
        if (i > n - fade) f = (double)(n - i) / fade;
        return Math.Max(0, Math.Min(1, f));
    }

    private static byte[] BuildWav(Func<int, int, double> sampleAt, int rate, int totalSamples) {
        byte[] data = new byte[totalSamples * 2];
        for (int i = 0; i < totalSamples; i++) {
            double v = sampleAt(i, rate);
            short s = (short)Math.Max(-32767, Math.Min(32767, v * 32767));
            data[i * 2] = (byte)(s & 0xFF);
            data[i * 2 + 1] = (byte)((s >> 8) & 0xFF);
        }
        var ms = new System.IO.MemoryStream();
        var bw = new System.IO.BinaryWriter(ms);
        bw.Write(new byte[] { (byte)'R', (byte)'I', (byte)'F', (byte)'F' });
        bw.Write(36 + data.Length);
        bw.Write(new byte[] { (byte)'W', (byte)'A', (byte)'V', (byte)'E' });
        bw.Write(new byte[] { (byte)'f', (byte)'m', (byte)'t', (byte)' ' });
        bw.Write(16);
        bw.Write((short)1);
        bw.Write((short)1);
        bw.Write(rate);
        bw.Write(rate * 2);
        bw.Write((short)2);
        bw.Write((short)16);
        bw.Write(new byte[] { (byte)'d', (byte)'a', (byte)'t', (byte)'a' });
        bw.Write(data.Length);
        bw.Write(data);
        bw.Flush();
        return ms.ToArray();
    }

    public static void PlayTone(double freq, double seconds, double amp, int rate) {
        int n = (int)(rate * seconds);
        byte[] wav = BuildWav((i, r) => Math.Sin(2 * Math.PI * freq * i / r) * amp * Envelope(i, n, r), rate, n);
        var ms = new System.IO.MemoryStream(wav);
        using (var sp = new System.Media.SoundPlayer(ms)) { sp.PlaySync(); }
    }

    public static void PlaySweep(double f1, double f2, double seconds, double amp, int rate) {
        int n = (int)(rate * seconds);
        double phase = 0;
        byte[] wav = BuildWav((i, r) => {
            double t = (double)i / n;
            double f = f1 + (f2 - f1) * t;
            phase += 2 * Math.PI * f / r;
            return Math.Sin(phase) * amp * Envelope(i, n, r);
        }, rate, n);
        var ms = new System.IO.MemoryStream(wav);
        using (var sp = new System.Media.SoundPlayer(ms)) { sp.PlaySync(); }
    }
}
"@
}

function Get-DevicesSafe {
    param([int]$Flow)
    try { return @([AudioKit]::EnumDevices($Flow, 15)) }
    catch {
        Write-Warning ("无法枚举全部端点(flow={0})，降级为 ACTIVE+DISABLED（通常是有不在位端点的驱动状态卡住）。{1}" -f $Flow, $_.Exception.Message)
    }
    try { return @([AudioKit]::EnumDevices($Flow, 3)) }
    catch {
        try { return @([AudioKit]::EnumDevices($Flow, 1)) }
        catch { return @() }
    }
}

function Get-RenderDevices { Get-DevicesSafe 0 }
function Get-CaptureDevices { Get-DevicesSafe 1 }

function Get-StateText {
    param([int]$State)
    switch ($State -band 0xF) {
        1 { 'ACTIVE' }
        2 { 'DISABLED' }
        4 { 'NOTPRESENT' }
        8 { 'UNPLUGGED' }
        default { "STATE($State)" }
    }
}

function Test-VirtualAudioDevice {
    param($Device)
    if ($null -eq $Device) { return $false }
    if ($Device.Enumerator -in @('ROOT', 'SWD')) { return $true }
    if ($Device.Name -match '虚拟|Virtual|VB-|CABLE|VoiceMeeter|Steam Streaming|Broadcast|Mirroring|Nahimic|SoundWire|远程|Remote') { return $true }
    return $false
}
