import os
import subprocess
import time
import cv2
import numpy as np

device = "/dev/video4"
save_dir = "dataset_captures"
temp_video = "temp_orbit.avi"
os.makedirs(save_dir, exist_ok=True)

# --- Session Settings ---
STARTUP_DELAY_SEC = 4.0     # Countdown to get into position
RECORD_SECONDS = 90      # Record for 25 seconds while smoothly orbiting the object
TARGET_IMAGES = 500         # Automatically extracts the 300 sharpest frames from the recording

# 1. Configure native 640x480 YUYV with clean factory colors and bright exposure
subprocess.run([
    "v4l2-ctl", "-d", device,
    "--set-fmt-video=width=640,height=480,pixelformat=YUYV",
    "--set-parm=30",
    "--set-ctrl=auto_exposure=1",
    "--set-ctrl=exposure_time_absolute=620",
    "--set-ctrl=focus_automatic_continuous=1",
    "--set-ctrl=backlight_compensation=10",
    "--set-ctrl=gamma=125",
    "--set-ctrl=brightness=0",
    "--set-ctrl=contrast=8",
    "--set-ctrl=saturation=36"
], check=True)

cam = cv2.VideoCapture(device, cv2.CAP_V4L2)
cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Lossless/near-lossless fast MJPG container for temporary capture
fourcc = cv2.VideoWriter_fourcc(*'MJPG')
writer = cv2.VideoWriter(temp_video, fourcc, 20.0, (640, 480))

start_time = time.time()
recorded_frames = 0

print("Get ready! Orbit smoothly around your object once recording starts...")

while True:
    ret, frame = cam.read()
    if not ret or frame is None:
        continue

    now = time.time()
    elapsed = now - start_time
    preview = frame.copy()

    if elapsed < STARTUP_DELAY_SEC:
        rem = STARTUP_DELAY_SEC - elapsed
        cv2.putText(preview, f"GET READY: {rem:.1f}s", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    else:
        rec_elapsed = elapsed - STARTUP_DELAY_SEC
        if rec_elapsed >= RECORD_SECONDS:
            break

        writer.write(frame)
        recorded_frames += 1

        rem_rec = RECORD_SECONDS - rec_elapsed
        cv2.putText(preview, f"RECORDING: {rem_rec:.1f}s left ({recorded_frames} frames)", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        cv2.putText(preview, "Move smoothly around the object at different heights!", (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    cv2.imshow("Fast Orbit Recorder", preview)
    if cv2.waitKey(1) & 0xFF in (ord('k'), ord('q')):
        break

writer.release()
cam.release()
cv2.destroyAllWindows()

# --- Stage 2: Extract the sharpest frame from every time bucket ---
print(f"\nRecorded {recorded_frames} raw frames. Selecting the {TARGET_IMAGES} sharpest images...")

cap = cv2.VideoCapture(temp_video)
all_frames = []
while True:
    ret, f = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    center = gray[h//4 : 3*h//4, w//4 : 3*w//4]
    sharpness = float(cv2.Laplacian(center, cv2.CV_64F).var())
    all_frames.append((sharpness, f))
cap.release()

if len(all_frames) > 0:
    # Split recording into TARGET_IMAGES evenly spaced chunks and pick the sharpest frame in each chunk
    num_chunks = min(TARGET_IMAGES, len(all_frames))
    chunks = np.array_split(np.arange(len(all_frames)), num_chunks)

    saved_count = 0
    for idx_list in chunks:
        if len(idx_list) == 0:
            continue
        best_idx = max(idx_list, key=lambda i: all_frames[i][0])
        best_sharpness, best_frame = all_frames[best_idx]
        out_path = os.path.join(save_dir, f"img_{(saved_count+500):05d}.jpg")
        cv2.imwrite(out_path, best_frame, [cv2.IMWRITE_JPEG_QUALITY, 98])
        saved_count += 1

    os.remove(temp_video)
    print(f"Done! Saved {saved_count} sharp, clean 640x480 images to '{save_dir}/'.")
else:
    print("No frames were recorded.")
