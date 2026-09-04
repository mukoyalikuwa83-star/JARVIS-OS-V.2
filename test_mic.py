"""Test all microphone devices and find the working one."""
import sounddevice as sd
import numpy as np
import time

print("=== MICROPHONE DEVICE TEST ===\n")
devices = sd.query_devices()
print(f"Total devices: {len(devices)}\n")

working_mics = []
for i, d in enumerate(devices):
    if d['max_input_channels'] < 1:
        continue
    if 'stereo mix' in d['name'].lower():
        continue
    print(f"Testing device {i}: {d['name']} ({d['max_input_channels']} ch, default_sr={d.get('default_samplerate', '?')})")
    
    for sr in [16000, 44100, 48000]:
        try:
            audio = []
            def cb(indata, frames, time_info, status):
                audio.append(indata.copy())
            
            with sd.InputStream(samplerate=sr, channels=1, dtype='int16',
                                blocksize=512, callback=cb, device=i):
                time.sleep(0.5)
            
            if audio:
                all_audio = np.concatenate(audio)
                rms = float(np.sqrt(np.mean(all_audio.astype(np.float32) ** 2)))
                peak = float(np.max(np.abs(all_audio.astype(np.float32))))
                print(f"  {sr}Hz: RMS={rms:.1f}, Peak={peak:.1f} -> {'WORKING' if rms > 1 else 'QUIET'}")
                if rms > 1:
                    working_mics.append((i, d['name'], sr, rms))
        except Exception as e:
            print(f"  {sr}Hz: FAILED ({e})")
    print()

print("\n=== RESULTS ===")
if working_mics:
    best = max(working_mics, key=lambda x: x[3])
    print(f"Best mic: device {best[0]} ({best[1]}) at {best[2]}Hz, RMS={best[3]:.1f}")
    print(f"\nUse _MIC_DEVICE_ID = {best[0]}")
    print(f"Use SEND_SAMPLE_RATE = {best[2]}")
else:
    print("No working microphone found!")
    print("\nAll input devices:")
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            print(f"  {i}: {d['name']}")
