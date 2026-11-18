import os, cv2, array, sys, ast, time
import numpy as np
import onnxruntime as ort
import multiprocessing.dummy as mp

argCount = len(sys.argv) - 1
providers = [
    (
        "WebGpuExecutionProvider",
        {
            "enableGraphCapture": "1",
            "powerPreference": "high-performance",
        },
    ),
    "CPUExecutionProvider",
]
models = array.array[argCount]
thresh = 60.0
totalTime = 0

img = cv2.imread("source.png")

def sharpen(img, amount=1.5):
  blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=1.5)
  return cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)

def findobj(img):
    global totalTime, thresh, sessions

    outimg = img.copy()

    #Pre-process image into compatible format
    blob = cv2.resize(img, (640, 640))
    blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))  # Convert to (3, 640, 640)
    blob = np.expand_dims(blob, axis=0)   # Add batch dimension -> (1, 3, 640, 640)

    #Iterate over all sessions of onnx runtime
    for session in sessions:
        final_detections = []
        orig_h, orig_w = img.shape[:2]

        inferStart = time.perf_counter()
        objects = session.run(None, {session.get_inputs()[0].name: blob})
        inferEnd = time.perf_counter()
        totalTime += inferEnd-inferStart

        for i, obj in enumerate(objects):
            predictions = np.squeeze(obj, axis=0)
            predictions = np.transpose(predictions)

            boxes = predictions[:, :4]
            scores = predictions[:, 4:]
            confidences = np.max(scores, axis=1)
            print(np.max(confidences))

            # 3. Coordinate Filter & Non-Max Suppression
            mask = confidences > thresh/100.0
            filtered_boxes = boxes[mask]
            filtered_confidences = confidences[mask]

            boxes_xyxy = []
            for box in filtered_boxes:
                cx, cy, w, h = box

                # FIX 1: Correctly calculate standard bounding edges in 640 space first
                x1 = cx - (w / 2.0)
                y1 = cy - (h / 2.0)
                x2 = cx + (w / 2.0)
                y2 = cy + (h / 2.0)
                boxes_xyxy.append([x1, y1, x2, y2])

            indices = cv2.dnn.NMSBoxes(boxes_xyxy, filtered_confidences.tolist(), thresh/100.0, 0.45)

            # 4. Render Geometries (Thickened & Correctly Scaled)
            if len(indices) > 0:
                # FIX 2: Aggressive Resolution Scaler
                # Dynamically calculates optimal drawing weights based on true image height
                box_thickness = max(12, int(orig_h / 100))
                font_thickness = max(4, int(box_thickness / 3))
                font_scale = max(1.2, orig_h / 800)

                for idx in indices.flatten():
                    x1, y1, x2, y2 = boxes_xyxy[idx]
                    score = filtered_confidences[idx]

                    #print("Saving instance")
                    rx1 = int((x1 / 640.0) * orig_w)
                    ry1 = int((y1 / 640.0) * orig_h)
                    rx2 = int((x2 / 640.0) * orig_w)
                    ry2 = int((y2 / 640.0) * orig_h)

                    rx1, ry1 = max(0, rx1), max(0, ry1)
                    rx2, ry2 = min(orig_w, rx2), min(orig_h, ry2)

                    names_dict = ast.literal_eval(session.get_modelmeta().custom_metadata_map["names"])
                    name = next(iter(names_dict[i].values()))

                    final_detections.append({
                        "box": [rx1, ry1, rx2, ry2],
                        "confidence": float(score),
                        "name": name
                    })

                    # FIX 4: Apply the heavy thickness parameters to the drawing engines
                    cv2.rectangle(outimg, (rx1, ry1), (rx2, ry2), (0, 255, 0), box_thickness)

                    label = name + f": {score*100:.1f}%"
                    text_offset = max(40, int(box_thickness * 2.0))

                    cv2.putText(outimg, label, (rx1, max(text_offset, ry1 - int(box_thickness * 0.7))), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), font_thickness)
                    output = "detections.png"
                    cv2.imwrite(output, outimg)

    return final_detections, outimg

def init(image, modelPaths):
    global blob, sessions
    if len(modelPaths) == 0:
        print("ERROR: No models given!")
        print("Usage: detect.py <Path-to-model> <Path-to-model> <...>")
        return 0

    #ONNX Session options
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL


    #Set up ONNX Runtime sessions
    sessions = [
        ort.InferenceSession(path, sess_options=opts, providers=providers)
        for path in modelPaths
    ]
    for sesh in sessions:
        print("Session provider: ")
        print(sesh.get_providers())

    startTime = time.perf_counter()
    findobj(img)
    endTime = time.perf_counter()

    return 1

init(img, sys.argv[1:])
