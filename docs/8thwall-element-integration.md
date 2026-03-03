# 8thwall Elements Applied to Body Fit Viewer

Updated: 2026-03-03

## What was adopted

From `8thwall/web`, we adopted the **camera pipeline module** pattern used in Three.js examples.

- Source concept: `XR8.addCameraPipelineModules([...])`
- Local adaptation: `LiveCameraPipeline` in `viewer/body-fit/viewer.js`

This project does **not** copy XR8 runtime code. It applies the architecture idea to our existing webcam + pose pipeline.

## Current implementation

`viewer/body-fit/viewer.js` now has:

1. `LiveCameraPipeline`
2. `createPoseLandmarkerPipelineModule(viewer)`
3. `createPoseSegmentsPipelineModule(viewer)`

Lifecycle mapping:

- `onStart`: initialize resources (MediaPipe landmarker)
- `onUpdate`: process each frame (detect landmarks -> build live segments)
- `onStop`: release resources (close landmarker)

## Runtime behavior

When `Start WebCam` is clicked:

1. webcam stream starts
2. pipeline modules start
3. each render tick runs pipeline update

When `Stop Live` is clicked:

1. pipeline modules stop in reverse order
2. media tracks are released
3. viewer returns to inactive state

Meta panel now includes:

- `live_pipeline_active`
- `live_pipeline_modules`
- `live_pipeline_error`
- `live_pose_model`
- `live_pose_quality`
- `live_pose_reliable_joints`

Tracking quality guardrails in current implementation:

- uses MediaPipe confidence thresholds (`detection/presence/tracking`)
- rejects low-visibility joints before suit/VRM drive
- requires torso anchors (left/right shoulders + hips) before full update
- falls back to last stable frame when confidence drops

## Why this is useful

- easier extension: new live-input logic can be added as modules
- smaller blast radius: each feature has clear lifecycle ownership
- closer mental model to 8thwall examples, so later XR8 migration is straightforward

## Next step candidates

1. Add a smoothing module (`onUpdate`) for jitter reduction only.
2. Add an analytics module (`onUpdate`) for latency/fps/missed-frame stats.
3. Add optional XR8 bridge module gated by config + app key.
