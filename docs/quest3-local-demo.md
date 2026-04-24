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

## Exhibition Operation Modes

For an event booth, do not assume personal tethering will be stable. The demo should be prepared with three explicit modes:

- `cloud`: public visitor path. Serve the Quest app from HTTPS hosting such as Vercel and route Whisper/TTS through a server-side API. Use this when the organizer-provided line is available.
- `local`: rehearsal/operator path. Use the current local Python/Vite bridge on a booth-owned router or trusted LAN. Avoid relying on shared venue Wi-Fi for Quest-to-PC local access because client isolation is common.
- `demo`: emergency fallback. Skip live Whisper/TTS and complete deposition from a controller/menu trigger with pre-baked audio. This keeps the transformation experience available when the line is poor.

Future implementation should add a visible VR health panel that shows the active mode, API status, mic permission, last transcript, trigger match, latency, and whether demo fallback is ready.

## Controls

- `Enter VR`: uses IWSDK `world.launchXR()` to request an `immersive-vr` session.
- `Voice`: records audio, sends it to Sakura Whisper, detects `生成`, synthesizes the explanation TTS, and loads the returned replay.
- `Replay`: plays the current deposition replay again and plays TTS if an audio file exists.
- `Pause`: pauses or resumes the replay.
- `Reset`: returns the replay to the beginning.

Query options:

- `?mocopiLive=1` or `?tracking=mocopi-live`: polls the local mocopi live bridge and uses the recent live frame buffer when the voice trigger succeeds.
- `?mockTrigger=1`: developer-only smoke test that skips remote STT/TTS and treats the trigger as detected.
- No mock flag: posts recorded audio to Sakura Whisper and starts deposition only when the transcript contains `生成`.
- Default voice capture is browser-encoded mono `audio/wav`, because Sakura AI Engine's Whisper guide recommends trying common formats such as MP3/WAV and monaural audio when transcription fails.
- `?audio=webm`: switches back to the old MediaRecorder WebM/Opus path for comparison.
- `?bgm=1&bgmSrc=/path/to/loop.mp3`: enables an optional BGM loop. BGM is off by default, and no generated low-frequency drone is played.
- `?seconds=4`: changes microphone recording length. The Quest demo default is now `4.5` seconds.
- `?armDelay=2`: changes the microphone arming delay before the UI switches from `MIC ARMING` to `SPEAK NOW`. The default is `1.4` seconds.
- `?suitspec=/sessions/<id>/suitspec.json`: uses another SuitSpec for mesh texture paths.
- `?mocopi=examples/mocopi_sequence.sample.json`: selects the mocopi/IWSDK pose JSON sent with voice requests.

## mocopi Live Bridge Contract

Quest Browser cannot receive mocopi UDP directly. For live tracking, run a PC-side bridge that receives mocopi data and forwards normalized frames to the local API.

Start the local API first:

```powershell
python tools\run_henshin.py serve-dashboard --port 8010 --root .
```

Then start the PC bridge in another terminal:

```powershell
npm run mocopi:bridge
```

Equivalent direct command:

```powershell
python tools\run_henshin.py mocopi-bridge --port 12351 --endpoint http://127.0.0.1:8010/api/iw-henshin/mocopi-live/frame
```

For mocopi app testing, set the external device IP to the notebook PC's LAN IP, set the outbound port to `12351`, and choose the app transfer format that matches the bridge adapter being tested. The bridge currently accepts JSON-style packets and simple OSC-style joint position messages; native mocopi binary packets need a Motion Serializer adapter.

Push one frame or a batch of frames:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8010/api/iw-henshin/mocopi-live/frame -ContentType "application/json" -Body '{
  "frames": [
    {
      "dt_sec": 0.1,
      "bones": {
        "LeftShoulder": [0.62, 0.38],
        "RightShoulder": [0.38, 0.38],
        "LeftHip": [0.57, 0.58],
        "RightHip": [0.43, 0.58],
        "RightHand": [0.225, 0.625]
      }
    }
  ]
}'
```

Check the latest frame and body-axis lock:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/api/iw-henshin/mocopi-live/latest
```

Open Quest demo with live buffer enabled:

```text
https://<PC LAN IP>:5173/viewer/quest-iw-demo/?mocopiLive=1
```

For exhibition/debug visibility, `?mocopiLive=1` now also shows a VR-side `MOCOPI LIVE` panel with a simplified live skeleton, joint count, frame age, and body-axis lock state. Use this first when you need to prove that mocopi is actually reaching the Quest experience. Add `&mocopiDebug=0` only when you want to hide that demo panel.

If the panel stays `STALE`, read the second line:

- `UDP: 0 packets received`: the PC bridge is running, but the phone/mocopi sender is not reaching the PC. Check the PC LAN IP, phone Wi-Fi, UDP port `12351`, and Windows firewall/private-network permission.
- `UDP: <n> rx / <n> unsupported`: packets are reaching the PC, but the transfer format is not one of the current JSON/simple-OSC adapters. Add or select the Motion Serializer/native mocopi adapter next.
- `UDP: <n> rx / <m> frames`: the bridge is forwarding frames. If this still appears stale, the sender has stopped or is sending too slowly for live tracking.

## Voice Debug Checklist

When the VR menu reaches `ANALYZING` and then `RETRY VOICE`, open/read the `Voice debug` panel. The same short diagnostic also appears in the VR menu:

- `Whisper heard: ...`: Sakura Whisper returned text, but it did not include exact `生成`.
- `Whisper returned an empty transcript`: the uploaded audio was silent, too quiet, malformed, or unreadable by Whisper.
- `peak` and `rms`: rough input level. If `quiet` appears, Quest Browser likely did not capture the intended mic signal.
- `Saved: /sessions/<id>/artifacts/voice-command.wav`: open this URL from desktop or Quest Browser to hear the exact audio that was sent to Sakura.

Near-miss transcripts are intentionally accepted while the voice window is active:

- Exact: `生成`
- Near miss: `先生`, `先生です`, `せいせい`, `せえせえ`, `せーせー`, `せいぜい`, `精製`, `精製します`, `セイセイ`, `セーセー`
