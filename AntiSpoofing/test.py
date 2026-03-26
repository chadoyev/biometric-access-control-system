import os
import cv2
import numpy as np
import argparse
import warnings
import time
from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name
warnings.filterwarnings('ignore')

cap = cv2.VideoCapture(0)  # For Webcam
cap.set(3, 640)
cap.set(4, 480)

def test(image, model_dir, device_id):
    model_test = AntiSpoofPredict(device_id)
    image_cropper = CropImage()
    image_bbox = model_test.get_bbox(image)
    prediction = np.zeros((1, 3))
    test_speed = 0
    # суммировать прогноз на основе результата одной модели
    for model_name in os.listdir(model_dir):
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        param = {
            "org_img": image,
            "bbox": image_bbox,
            "scale": scale,
            "out_w": w_input,
            "out_h": h_input,
            "crop": True,
        }
        if scale is None:
            param["crop"] = False
        img = image_cropper.crop(**param)
        start = time.time()
        prediction += model_test.predict(img, os.path.join(model_dir, model_name))
        test_speed += time.time()-start

    # нарисовать результат предсказания
    label = np.argmax(prediction)
    value = prediction[0][label]/2
    if label == 1:
        print("Real. Score: {:.2f}.".format(value))
        result_text = "Real Score: {:.2f}".format(value)
        color = (0, 128, 0)
    else:
        print("Fake. Score: {:.2f}.".format(value))
        result_text = "Fake Score: {:.2f}".format(value)
        color = (0, 0, 255)
    print("Prediction cost {:.2f} s".format(test_speed))
    cv2.rectangle(
        image,
        (image_bbox[0], image_bbox[1]),
        (image_bbox[0] + image_bbox[2], image_bbox[1] + image_bbox[3]),
        color, 2)
    cv2.putText(
        image,
        result_text,
        (image_bbox[0], image_bbox[1] - 5),
        cv2.FONT_HERSHEY_COMPLEX, 1.5*image.shape[0]/1024, (255, 255, 255), 2)
    return image


if __name__ == "__main__":
    while True:
        success, img = cap.read()
        if success:
            img2 = test(img, "./resources/anti_spoof_models", 0)
            cv2.imshow("Image", img2)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
