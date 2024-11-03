import numpy as np
from ultralytics import YOLO
import cv2
import math
import time
import os
from datetime import datetime

def yolo_detection():
    video_path = os.getenv("VIDEO_PATH", "C:/Users/axttt/PycharmProjects/pythonProject/test.mp4")
    model = YOLO(os.getenv("YOLO_MODEL", "best.pt"))

    classNames = ["fall", "normal"]
    cap = cv2.VideoCapture(video_path)

    prevClass = "Non detection"
    currentClass = None
    fall_count = 0
    last_fall_frame = None
    save_interval = 10
    start_time = None
    is_image_saved = False

    save_folder = os.getenv("SAVE_FOLDER", r"C:\Users\axttt\PycharmProjects\pythonProject\static\media")
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    image_files = [f for f in os.listdir(save_folder) if f.endswith('.jpg')]
    video_files = [f for f in os.listdir(save_folder) if f.endswith('.mp4')]

    image_counter = len(image_files)
    video_counter = len(video_files)

    fourcc = cv2.VideoWriter_fourcc(*'avc1')

    while True:
        success, img = cap.read()
        if not success:
            break

        results = model(img, stream=True)
        detections = np.empty((0, 5))
        totalFall = 0
        totalNormal = 0

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                conf = math.ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                currentClass = classNames[cls]

                if currentClass in classNames and conf > 0.50:
                    detections = np.vstack((detections, np.array([x1, y1, x2, y2, conf])))

                    label = f'{currentClass}: {conf:.2f}'
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255) if currentClass == "normal" else (0, 0, 255), 2)
                    cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                    if currentClass == "fall":
                        totalFall += 1
                        if start_time is None:
                            start_time = time.time()

                        if time.time() - start_time >= 10:
                            image_counter += 1
                            last_fall_frame = img.copy()
                            date_str = datetime.now().strftime("%Y-%m-%d")
                            image_save_path = os.path.join(save_folder, f"{date_str}_ảnh_{image_counter}.jpg")
                            cv2.imwrite(image_save_path, last_fall_frame)
                            print(f"Đã lưu ảnh: {image_save_path}")

                            video_counter += 1
                            video_save_path = os.path.join(save_folder, f"{date_str}_video_{video_counter}.mp4")
                            video_out = cv2.VideoWriter(video_save_path, fourcc, 20.0, (img.shape[1], img.shape[0]))
                            video_start_time = time.time()

                            for _ in range(int(10 * 20)):
                                success, frame = cap.read()
                                if not success:
                                    break
                                video_out.write(frame)

                            video_out.release()
                            print(f"Đã lưu video: {video_save_path}")

                            is_image_saved = True
                            start_time = None
                    else:
                        if is_image_saved:
                            is_image_saved = False
                            start_time = None
                    totalNormal += 1

        cv2.imshow("YOLO Detection", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Chạy nhận diện té ngã
if __name__ == '__main__':
    yolo_detection()
