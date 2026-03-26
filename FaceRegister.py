import face_recognition
from imutils import paths
import os
import cv2
import pickle
script_path = os.path.abspath(__file__)
dir_path = os.path.dirname(script_path)

imagePaths = list(paths.list_images(f'{dir_path}/files'))
knownEncodings = []
knownNames = []


for (i, imagePath) in enumerate(imagePaths):
    try:
        name = imagePath.split(os.path.sep)[-2]
        if name == "123456":
            continue
        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model='hog')
        encodings = face_recognition.face_encodings(rgb, boxes)
        for encoding in encodings:
            knownEncodings.append(encoding)
            knownNames.append(name)

    except Exception as e:
        continue

data = {"encodings": knownEncodings, "names": knownNames}
with open(f"{dir_path}/face_enc", "wb") as f:
    pickle.dump(data, f)
