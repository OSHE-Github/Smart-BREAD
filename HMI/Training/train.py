import os, glob, json, shutil, warnings, sys, time
import multiprocessing.dummy as mp

#Automatic dependency install
try:
    import ultralytics, torch, cv2
    import numpy as np
except ImportError:
    import subprocess
    print("Installing Ultralytics YOLO framework...")
    subprocess.check_call(["pip", "install", "ultralytics", "torch", "opencv-python", "numpy"])

import torch, cv2
from ultralytics import YOLO
import numpy as np


#Training variable definitions
numEpochs = 100
imgSize = 640
batchSize = 16
workerThreads = 16
argCount = len(sys.argv) - 1

#Time debugging stuff
timeDebug = 1
if timeDebug:
    startTime = time.perf_counter()

def main(trainData, subject):
    if not os.path.exists(trainData):
        print(f"Error: Directory '{trainData}' does not exist.")
        return

    #Convert Anylabeling to YOLO format
    print("\nParsing AnyLabeling JSON files and preparing data layout...")

    #Yolo Directory creation
    yoloData = os.path.join(os.path.dirname(trainData), "yolo_dataset")
    yoloImgDir = os.path.join(yoloData, "images", "train")
    yoloLabelDir = os.path.join(yoloData, "labels", "train")
    os.makedirs(yoloImgDir, exist_ok=True)
    os.makedirs(yoloLabelDir, exist_ok=True)

    #Iterate over all supported extensions and check if images match the correct extensions
    valid_extensions = ("*.jpg", "*.jpeg", "*.png", "*.BMP")
    trainDataPaths = []
    for ext in valid_extensions:
        trainDataPaths.extend(glob.glob(os.path.join(trainData, ext)))
        trainDataPaths.extend(glob.glob(os.path.join(trainData, ext.upper())))

    #Convert anylabeling JSONS to a format YOLO can use
    def convertJsons(path):
        global converted_count
        pathJson = os.path.splitext(path)[0] + ".json"

        #Only process images that have json labels
        if os.path.exists(pathJson):
            name = os.path.basename(path)

            #Read source image for original dimensions
            temp_img = cv2.imread(path)
            if temp_img is None:
                return
            imgHeight, imgWidth = temp_img.shape[:2]

            #Read JSON file for properties
            f = open(pathJson, "r")
            data = json.load(f)
            f.close()

            lines = []
            for shape in data.get("shapes", []):
                if shape.get("label") == subject and shape.get("shape_type") == "rectangle":
                    points = shape.get("points", [])
                    if len(points) == 2:
                        x1, y1 = points[0]
                        x2, y2 = points[1]

                        # Calculate box centers and relative dimensions
                        xmin, xmax = min(x1, x2), max(x1, x2)
                        ymin, ymax = min(y1, y2), max(y1, y2)

                        #Calculate box width, height, and centerpoint coordinates
                        bWidth = xmax - xmin
                        bHeight = ymax - ymin

                        #Normalize coordinates between 0 and 1
                        normCenterX = (xmin + (bWidth / 2.0)) / imgWidth
                        normCenterY = (ymin + (bHeight / 2.0)) / imgHeight
                        normbWidth = bWidth / imgWidth
                        normbHeight = bHeight / imgHeight

                        #Format so YOLO can understand it: x_center y_center width height
                        lines.append(f"0 {normCenterX:.6f} {normCenterY:.6f} {normbWidth:.6f} {normbHeight:.6f}")

            if len(lines) > 0:
                #Copy assets into training workspace cleanly
                shutil.copy(path, os.path.join(yoloImgDir, name))

                #Save label to the workspace
                f = open(os.path.join(yoloLabelDir, os.path.splitext(name)[0] + ".txt"), "w")
                f.write("\n".join(lines))
                f.close()

    #Multithread the json conversion for faster execution
    p=mp.Pool(workerThreads)
    p.map(convertJsons,trainDataPaths)
    p.close()
    p.join()

    initTime = time.perf_counter()
    if timeDebug:
        print(f"Time to convert: {round((initTime - startTime), 2)}s")

    #Agonizing YAML File formatting
    yaml_path = os.path.join(yoloData, "dataset.yaml")
    yaml_content = f"""path: {os.path.abspath(yoloData)}
train: images/train
val: images/train  # Fallback to train for single-dataset optimization sets

names:
  0: {subject}
"""

    #Write YAML to disk
    f = open(yaml_path, "w")
    f.write(yaml_content.strip())
    f.close()

    #Initialize devices and train the model.
    print("\nInitializing Nano YOLOv8 (yolov8n.pt) edge-optimized graph...")
    model = YOLO("yolov8n.pt")

    #Check for NVIDIA hardware for acceleration of training process
    if torch.cuda.is_available():
        print(f"\nCUDA enabled device found: [{torch.cuda.get_device_name(0)}]")
        device = 0
        cacheFlag = True
    else:
        print("\nNo CUDA enabled device found: Falling back on CPU compute...")
        device = "cpu"
        cacheFlag = False

    #Train the model on specified device with specified flags attached
    print(f"Launching training on device: {str(device).upper()}...")
    model.train(data=yaml_path, epochs=numEpochs, imgsz=imgSize, batch=batchSize, device=device, workers=workerThreads, cache=cacheFlag)

    print("\nTraining completed successfully! Clean weights saved.")

    #Export as .pt and .onnx for use on multiple systems.
    print("\nTraining completed successfully! Committing weight outputs...")

    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)  # Creates the directory automatically if missing

    #Define names for the output files
    pyTorchModelPath = os.path.join(models_dir, subject+".pt")
    onnxModelPath = os.path.join(models_dir, subject+".onnx")

    #Try to save the models to disk
    try:
        #Save the .pt model to the disk
        shutil.copy(model.trainer.best, pyTorchModelPath)
        print(f"PyTorch model saved to:\n    [{pyTorchModelPath}]")

        #Create and save model as onnx for high efficiency runtime
        print("Compiling ONNX model...")
        shutil.move(model.export(format="onnx"), onnxModelPath)
        print(f"ONNX Model saved to:\n    [{onnxModelPath}]")

    except Exception as e:
        print(f"Automated export warning encountered: {e}")
        print("Please check your 'runs/detect/train/weights/' directory for standard backups.")



if __name__ == "__main__":
    if argCount == 2:
        trainData = sys.argv[1]
        subject = sys.argv[2]
    else:
        trainData = input("Enter the path to the training data: ").strip()
        subject = input("Enter the name of the object to find: ").strip()

    main(trainData, subject)

