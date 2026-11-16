import os, cv2, array, sys, ast
import numpy as np
import onnxruntime as ort

argCount = len(sys.argv) - 1
providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
models = array.array[argCount]
thresh = 70.0

img = cv2.imread("/home/bradley/Documents/GitHub/Smart-BREAD/HMI/Training/20261115_165515.jpg")
outimg = img.copy()


def findobj(cv2_image, session, input_name, thresh):
    global outimg

    orig_h, orig_w = cv2_image.shape[:2]
    annotated_image = cv2_image.copy()

    # 1. High-Speed Preprocessing
    blob = cv2.resize(cv2_image, (640, 640))
    blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))  # Convert to (3, 640, 640)
    blob = np.expand_dims(blob, axis=0)   # Add batch dimension -> (1, 3, 640, 640)

    # 2. Hardware Accelerated Inference Pass
    infer_result = session.run(None, {input_name: blob})[0]

    # Transpose output matrix shape [1, 5, 8400] -> [8400, 5]
    predictions = np.squeeze(infer_result, axis=0)
    predictions = np.transpose(predictions)

    boxes = predictions[:, :4]
    scores = predictions[:, 4:]
    confidences = np.max(scores, axis=1)

    # 3. Coordinate Filter & Non-Max Suppression
    mask = confidences > thresh
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

    indices = cv2.dnn.NMSBoxes(boxes_xyxy, filtered_confidences.tolist(), thresh, 0.45)

    final_detections = []

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

            print("Saving instance")
            # FIX 3: Denormalize coordinates dynamically relative to the image's raw dimensions
            rx1 = int((x1 / 640.0) * orig_w)
            ry1 = int((y1 / 640.0) * orig_h)
            rx2 = int((x2 / 640.0) * orig_w)
            ry2 = int((y2 / 640.0) * orig_h)

            rx1, ry1 = max(0, rx1), max(0, ry1)
            rx2, ry2 = min(orig_w, rx2), min(orig_h, ry2)

            final_detections.append({
                "box": [rx1, ry1, rx2, ry2],
                "confidence": float(score)
            })

            # FIX 4: Apply the heavy thickness parameters to the drawing engines
            cv2.rectangle(outimg, (rx1, ry1), (rx2, ry2), (0, 255, 0), box_thickness)

            names_dict = ast.literal_eval(session.get_modelmeta().custom_metadata_map["names"])
            name = next(iter(names_dict.values()))

            label = name + f": {score*100:.1f}%"
            text_offset = max(40, int(box_thickness * 2.0))

            cv2.putText(outimg, label, (rx1, max(text_offset, ry1 - int(box_thickness * 0.7))), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), font_thickness)

    return final_detections

def main(sessions, image, outimg):

    for session in sessions:
        results = findobj(image,session,session.get_inputs()[0].name, thresh/100.0)
        print(f"\nLocated {len(results)} target instances.")
        for idx, item in enumerate(results):
            print(f" -> Object [{idx}]: Confidence: {item['confidence']*100:.1f}% | Coordinates: {item['box']}")

        output = "detections.png"
        cv2.imwrite(output, outimg)

if __name__ == "__main__":
    if argCount == 0:
        print("ERROR: No models given!")
        print("Usage: detect.py <Path-to-model> <Path-to-model> <...>")
        exit()

    #ONNX Session options
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    #Set up ONNX Runtime sessions
    sessions = [ort.InferenceSession(path, providers=providers) for path in sys.argv[1:]]

    print("Exec main")
    main(sessions, img, outimg)
