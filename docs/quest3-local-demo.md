# Quest 3 Local VR Demo

Updated: 2026-04-16

## What This Page Does

`viewer/quest-iw-demo` is the local Quest 3 test surface for the IW henshin flow. It is an Immersive Web SDK app, not a raw Three.js `ARButton` page.

- Loads existing `viewer/assets/meshes/*.mesh.json` armor meshes.
- Applies existing `texture_path` entries from `examples/suitspec.sample.json`.
- Creates an IWSDK `World` with `SessionMode.ImmersiveVR`.
- Enters the headset session through `world.launchXR({ sessionMode: SessionMode.ImmersiveVR })`.
- Records a short voice clip, posts it to `/api/iw-henshin/voice`, then runs Sakura AI Engine Whisper/TTS through the Python bridge.
- Replays the mocopi/IWSDK deposition result so the transformation can be reviewed again.

## Start The Local Servers

Terminal 1: Sakura/IW voice bridge API.

```powershell
python tools\run_henshin.py serve-dashboard --port 8010 --root .
```

Terminal 2: IWSDK/Vite Quest app.

```powershell
npm run dev:quest
```

PC browser check:

```text
http://localhost:5173/viewer/quest-iw-demo/
```

Mock-trigger check without Sakura calls:

```text
http://localhost:5173/viewer/quest-iw-demo/?mockTrigger=1
```

## Quest 3 Same-LAN Access

For the fastest headset check, do not start by installing the root CA. Try the warning-bypass path first:

1. Keep the API and Quest Vite servers running.
2. Open `https://<PC LAN IP>:5173/viewer/quest-iw-demo/` in Quest Browser.
3. If a certificate warning appears, choose `Advanced`, then `Proceed to <PC LAN IP>`.
4. Press `Enter VR`, then allow the WebXR prompt.
5. Press `Voice` and allow the microphone prompt.

If the page loads but `Enter VR` or microphone capture is blocked, switch to the HTTP flag path below.

### Skip Certificates With Quest Browser Flags

This is a development-only shortcut. It treats this one LAN origin as secure inside Quest Browser.

Stop the HTTPS Quest Vite server if it is using port `5173`, then start the normal HTTP server:

```powershell
npm run dev:quest
```

In Quest Browser:

1. Open `chrome://flags`.
2. Search for `insecure`.
3. Set `Insecure origins treated as secure` / `unsafely-treat-insecure-origin-as-secure` to `Enabled`.
4. In the origin text field, enter the exact origin:

```text
http://192.168.1.4:5173
```

5. Tap outside the field so the value is committed.
6. Tap `Relaunch`.
7. Open:

```text
http://192.168.1.4:5173/viewer/quest-iw-demo/?mockTrigger=1
```

If the PC LAN IP changes, update the flag value to the new exact origin and relaunch Quest Browser again.

### Persistent HTTPS Certificate Path

Quest Browser should open the Vite app over HTTPS when you are not using `localhost`.
The browser talks only to Vite on port `5173`; Vite proxies `/api` and `/sessions` to the Python server on `8010`, so the browser does not need to call the API port directly.

Create a LAN certificate. The repo includes a Windows-only helper that creates a local root CA, trusts it on this PC, adds the PC LAN IP as an `IPAddress` subject alternative name, and exports a Vite-readable PFX:

```powershell
.\tools\new_quest_lan_cert.ps1
```

Install/trust `config\quest-lan-root-ca.cer` on the Quest device if you want HTTPS without warning prompts. Then start the IWSDK app:

```powershell
npm run dev:quest:lan
```

If you already use `mkcert`, you can still use PEM files instead:

```powershell
mkcert -install
mkcert -cert-file config\quest-lan.pem -key-file config\quest-lan-key.pem 192.168.1.4 localhost 127.0.0.1
```

Open this from Quest Browser:

```text
https://<PC LAN IP>:5173/viewer/quest-iw-demo/
```

Example from the current network scan:

```text
https://192.168.1.4:5173/viewer/quest-iw-demo/
```

## Quest 3 Localhost Fallback

If same-LAN certificate trust is not ready yet, ADB reverse still works because Quest opens the app as `localhost`:

```powershell
adb devices
adb reverse tcp:5173 tcp:5173
adb reverse tcp:8010 tcp:8010
```

Then open this in Meta Quest Browser:

```text
http://localhost:5173/viewer/quest-iw-demo/
```

Plain LAN HTTP can show the 3D preview, but microphone capture and immersive VR may be blocked by browser security.

## Sakura AI Engine Env

Set these before starting the server:

```powershell
$env:SAKURA_AI_ENGINE_TOKEN="..."
$env:SAKURA_AI_ENGINE_BASE_URL="https://api.ai.sakura.ad.jp/v1"
$env:SAKURA_WHISPER_MODEL="whisper-large-v3-turbo"
$env:SAKURA_TTS_MODEL="zundamon"
$env:SAKURA_TTS_VOICE="normal"
$env:SAKURA_TTS_FORMAT="wav"
```

Equivalent `.env` keys are also read by the bridge.

## Controls

- `Enter VR`: uses IWSDK `world.launchXR()` to request an `immersive-vr` session.
- `Voice`: records audio, sends it to Sakura Whisper, detects `生成`, synthesizes the explanation TTS, and loads the returned replay.
- `Replay`: plays the current deposition replay again and plays TTS if an audio file exists.
- `Pause`: pauses or resumes the replay.
- `Reset`: returns the replay to the beginning.

Query options:

- `?mockTrigger=1`: developer-only smoke test that skips remote STT/TTS and treats the trigger as detected.
- No mock flag: posts recorded audio to Sakura Whisper and starts deposition only when the transcript contains `生成`.
- Default voice capture is browser-encoded mono `audio/wav`, because Sakura AI Engine's Whisper guide recommends trying common formats such as MP3/WAV and monaural audio when transcription fails.
- `?audio=webm`: switches back to the old MediaRecorder WebM/Opus path for comparison.
- `?bgm=1&bgmSrc=/path/to/loop.mp3`: enables an optional BGM loop. BGM is off by default, and no generated low-frequency drone is played.
- `?seconds=4`: changes microphone recording length. The Quest demo default is now `4.5` seconds.
- `?armDelay=2`: changes the microphone arming delay before the UI switches from `MIC ARMING` to `SPEAK NOW`. The default is `1.4` seconds.
- `?suitspec=/sessions/<id>/suitspec.json`: uses another SuitSpec for mesh texture paths.
- `?mocopi=examples/mocopi_sequence.sample.json`: selects the mocopi/IWSDK pose JSON sent with voice requests.

## Voice Debug Checklist

When the VR menu reaches `ANALYZING` and then `RETRY VOICE`, open/read the `Voice debug` panel. The same short diagnostic also appears in the VR menu:

- `Whisper heard: ...`: Sakura Whisper returned text, but it did not include exact `生成`.
- `Whisper returned an empty transcript`: the uploaded audio was silent, too quiet, malformed, or unreadable by Whisper.
- `peak` and `rms`: rough input level. If `quiet` appears, Quest Browser likely did not capture the intended mic signal.
- `Saved: /sessions/<id>/artifacts/voice-command.wav`: open this URL from desktop or Quest Browser to hear the exact audio that was sent to Sakura.

Near-miss transcripts are intentionally accepted while the voice window is active:

- Exact: `生成`
- Near miss: `先生`, `先生です`, `せいせい`, `せえせえ`, `せーせー`, `せいぜい`, `精製`, `精製します`, `セイセイ`, `セーセー`
