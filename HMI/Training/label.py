import os, sys, cv2, ast, json, threading, shutil
import numpy as np
import onnxruntime as ort

argCount = len(sys.argv) - 1


def objectDetect(cv2_image, session, confidence_threshold=0.25):
    input_name = session.get_inputs()[0].name

    # Extract class names from model with a safe fallback
    meta = session.get_modelmeta().custom_metadata_map
    if 'names' in meta:
        class_names = ast.literal_eval(meta['names'])
    else:
        class_names = {} # Fallback dictionary if metadata is missing

    orig_h, orig_w = cv2_image.shape[:2]
    annotated_image = cv2_image.copy()


    # 1. High-Speed Preprocessing
    blob = cv2.resize(cv2_image, (640, 640))
    blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))
    blob = np.expand_dims(blob, axis=0)

    # 2. Hardware Accelerated Inference Pass
    infer_result = session.run(None, {input_name: blob})[0] # Squeeze first index directly

    predictions = np.squeeze(infer_result, axis=0)
    predictions = np.transpose(predictions)

    boxes = predictions[:, :4]
    scores = predictions[:, 4:]

    # Dynamically extract the highest-scoring class index for each bounding box
    class_ids = np.argmax(scores, axis=1)
    confidences = np.max(scores, axis=1)

    # 3. Coordinate Filter & Non-Max Suppression
    mask = confidences > confidence_threshold

    # FIX: Explicitly index along axis 0 to filter rows, avoiding the shape mismatch error
    filtered_boxes = boxes[mask, :]
    filtered_confidences = confidences[mask]
    filtered_class_ids = class_ids[mask]

    boxes_xyxy = []
    for box in filtered_boxes:
        cx, cy, w, h = box
        x1 = cx - (w / 2.0)
        y1 = cy - (h / 2.0)
        x2 = cx + (w / 2.0)
        y2 = cy + (h / 2.0)
        boxes_xyxy.append([x1, y1, x2, y2])

    indices = cv2.dnn.NMSBoxes(boxes_xyxy, filtered_confidences.tolist(), confidence_threshold, 0.45)

    final_detections = []
    # 4. Render Geometries & Structure AnyLabeling Output
    if len(indices) > 0:
        box_thickness = max(12, int(orig_h / 100))
        font_thickness = max(4, int(box_thickness / 3))
        font_scale = max(1.2, orig_h / 800)

        for idx in indices.flatten():
            x1, y1, x2, y2 = boxes_xyxy[idx]
            score = filtered_confidences[idx]
            class_id = filtered_class_ids[idx]

            # Dynamically resolve label using the model's detected index
            if isinstance(class_names, dict):
                label_text = class_names.get(int(class_id), f"class_{class_id}")
            elif isinstance(class_names, (list, tuple)):
                label_text = class_names[int(class_id)] if int(class_id) < len(class_names) else f"class_{class_id}"
            else:
                label_text = f"class_{class_id}"

            # Denormalize coordinates relative to the image's raw dimensions
            rx1 = int((x1 / 640.0) * orig_w)
            ry1 = int((y1 / 640.0) * orig_h)
            rx2 = int((x2 / 640.0) * orig_w)
            ry2 = int((y2 / 640.0) * orig_h)

            rx1, ry1 = max(0, rx1), max(0, ry1)
            rx2, ry2 = min(orig_w, rx2), min(orig_h, ry2)

            # Format to AnyLabeling shape specifications
            final_detections.append({
                "label": label_text,
                "score": float(score),
                "points": [
                    [float(rx1), float(ry1)],
                    [float(rx2), float(ry2)]
                ],
                "shape_type": "rectangle",
                "flags": {}
            })

            # Render
            cv2.rectangle(annotated_image, (rx1, ry1), (rx2, ry2), (0, 255, 0), box_thickness)

            display_label = f"{label_text}: {score*100:.1f}%"
            text_offset = max(40, int(box_thickness * 2.0))

            cv2.putText(annotated_image, display_label, (rx1, max(text_offset, ry1 - int(box_thickness * 0.7))),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), font_thickness)

    return annotated_image, final_detections

def createLabel(image_path, final_detections):
    """
    Generates a companion .json file for an image in the strict AnyLabeling format.
    Automatically extracts image dimensions from the file path.

    :param image_path: Full path to the original source image (e.g., '/path/to/img.jpg')
    :param final_detections: The 'results' array returned by detect_objects_in_cv2_image
    """
    # Automatically extract structural image dimensions using OpenCV
    temp_img = cv2.imread(image_path)
    if temp_img is None:
        print(f"Error: Could not open or read image file at {image_path}")
        return None

    image_height, image_width = temp_img.shape[:2]

    # Extract structural file metadata properties
    image_filename = os.path.basename(image_path)
    base_name, _ = os.path.splitext(image_filename)
    image_dir = os.path.dirname(image_path)

    # Target absolute file path matching AnyLabeling sidecar requirements
    jsonsPath = os.path.join(image_dir, f"jsons/")
    labelPath = os.path.join(jsonsPath, f"{base_name}.json")

    # Construct complete AnyLabeling structural schema template
    imageLabel = {
        "version": "0.2.22",
        "flags": {},
        "shapes": final_detections,  # Inject your function output list array directly
        "imagePath": image_filename,
        "imageData": None,           # Kept null to prioritize clean loading and tiny file sizes
        "imageHeight": int(image_height),
        "imageWidth": int(image_width)
    }

    # Save the physical payload to disk
    shutil.copy(image_path, jsonsPath)
    f = open(labelPath, "w", encoding="utf-8")
    json.dump(imageLabel, f, indent=2, ensure_ascii=False)
    f.close()

    print(f"Success: AnyLabeling markup written to {labelPath}")
    return labelPath

def main(modelPath, imgPath, session):
    if not os.path.exists(modelPath):
        print(f"Error: ONNX file not found at {modelPath}")
        return
    if not os.path.exists(imgPath):
        print(f"Error: Input picture file '{imgPath}' not found.")
        return

    opened_cv2_image = cv2.imread(imgPath)
    if opened_cv2_image is None:
        print("Error: OpenCV failed to decode the picture file data matrix.")
        return

    #Check if output json already exists
    image_filename = os.path.basename(imgPath)
    base_name, _ = os.path.splitext(image_filename)
    image_dir = os.path.dirname(imgPath)
    json_output_path = os.path.join(image_dir, f"jsons/{base_name}.json")

    if not os.path.exists(json_output_path):
        processed_frame, results = objectDetect(opened_cv2_image, session)
    else:
        return

    print(f"\nLocated {len(results)} target instances.")
    for idx, item in enumerate(results):
        print(f" -> Object [{idx}]: Confidence: {item['score']*100:.1f}% | Coordinates: {item['points']}")

    dispFrame = cv2.resize(processed_frame, (960, 540))
    cv2.imshow("Processed Frame", dispFrame)
    if cv2.waitKey(1) & 0xFF == ord('k'):
        exit()
    else:
        if len(results) > 0:
            labelThread = threading.Thread(target = createLabel, args=(imgPath, results))
            labelThread.start()
        pass

if __name__ == "__main__":
    print("ONNX automatic image labeler")
    print("ONLY use when you have a small dataset already labeled and a model trained on that dataset")

    #Start the model up
    if argCount == 2:
        modelPath = sys.argv[1]
        dataDir = sys.argv[2]
    else:
        modelPath = input("Enter the path to your best.onnx file: ").strip()
        dataDir = input("Enter the path to the image to process: ").strip()

    print("\nInitializing Optimized ONNX Runtime Session...")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 20
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(modelPath, sess_options=opts, providers=['CPUExecutionProvider'])

    for path in os.scandir(dataDir):
        if path.is_file():
            main(modelPath, path, session)
