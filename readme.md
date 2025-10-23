# Cinecomic

Cinecomic is an automated movie-to-comic generator. Input a video and it generates a comic book for the same complete with a comic style and dialogue bubbles.

## Methodology

Our project consists of the following core modules:

1. **Subtitle Generation**
   - Create a subtitle file for the input video using Whisper model
2. **Keyframe Extraction**
   - Frame Sampling: Samples frames at a set frequency from videos.
   - Feature Extraction: Utilizes deep learning models like GoogLeNet v1 to extract features from frames.
   - Highlightness Score Calculation: Deep Summarization Network (DSN) computes scores to identify keyframes.
   - Dialogue Grouping: Groups frames based on dialogues to select significant keyframes.
3. **Panel Layout Generation**
   - Calculates the Region of Interest of a frame
   - Selects a page layout template
   - Crops frame to be accomodated into template
4. **Balloon Generation & Placement**
   - Analysis of emotions in subtitles determines speech balloon shape.
   - Balloon placement involves using the "Dlib" face-detector library to detect characters' mouth positions in frames and placing at regions with relatively lesser ROI.

## Pre-requisites

- Python
- Install [Pytorch](https://pytorch.org/get-started/locally/)
- Install [dlib](https://github.com/z-mahmud22/Dlib_Windows_Python3.x)
- Install ffmpeg
- All dependencies mentioned in `requirements.txt` to be installed. (`pip install -r requirements.txt`)

## Running the project

- If you are not using a GPU, head over to `backend/keyframes/keyframes.py` and set `gpu=False`(At exactly 2 locations)
- You can head over to `backend/subtitles/subs.py` and change the Whisper model used. (Check supported models [here](https://github.com/openai/whisper))
- Run the flask server: `python -m flask --app app run`
- Open the localhost link on your browser (Eg:`http://127.0.0.1:5000`)
