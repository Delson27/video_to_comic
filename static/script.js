const carousel = document.querySelector(".carousel");
const carouselItems = carousel.querySelectorAll(".carousel-item");
const submissionResult = document.getElementById("submissionResult");
const linkInput = document.getElementById("link-input");
const filePicker = document.getElementById("fileInput");
const videoPreview = document.getElementById("video-preview");
const iFramePreview = document.getElementById("iframe-preview");
const bgVideo = document.getElementById("bgVideo");
const submitButton = document.getElementById("submitButton");
const resultButtons = document.getElementById("resultButtons");

var selectedFile = null;
var selectedLink = "";
var linkInputVisible = false;
let currentItem = 0;

// 1. Background image carousel
function changeImage() {
  carouselItems.forEach((item, index) => {
    if (index === currentItem) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });
  currentItem = (currentItem + 1) % carouselItems.length;
}
setInterval(changeImage, 3000);

// 2. Box with title, description and (file uploader/link & submit button)
const box = document.querySelector(".box");
setTimeout(() => {
  box.classList.add("visible");
}, 2000);

// 3. File uploader
function openFilePicker() {
  hideLinkInput();
  filePicker.click();
}

filePicker.addEventListener("change", function () {
  selectedFile = this.files[0];
  if (selectedFile) {
    const fileSizeMB = (selectedFile.size / (1024 * 1024)).toFixed(2);
    document.getElementById("fileName").textContent =
      "✓ " + selectedFile.name + " (" + fileSizeMB + " MB)";
    document.getElementById("fileName").style.color = "#22c55e";
  }
  hideLinkInput();
  showVideoPreview(URL.createObjectURL(selectedFile));
});

// 4. Link
function toggleLinkInput() {
  hideVideoPreview();
  var linkInputContainer = document.getElementById("linkInputContainer");
  linkInputVisible = !linkInputVisible;
  if (linkInputVisible) {
    linkInputContainer.style.display = "block";
  } else {
    hideLinkInput();
  }
}

function hideLinkInput() {
  document.getElementById("linkInputContainer").style.display = "none";
  linkInput.value = "";
  selectedLink = "";
  hideIFramePreview();
}

function convertToEmbed(url) {
  // Regular expression to capture the video ID from the YouTube URL
  const videoIdPattern = /(?:v=|\/)([0-9A-Za-z_-]{11}).*/;
  const match = url.match(videoIdPattern);

  if (!match) {
    return null; // Return null if no video ID is found
  }

  const videoId = match[1];
  const embedUrl = `https://www.youtube.com/embed/${videoId}`;
  return embedUrl;
}

linkInput.addEventListener("input", function () {
  selectedLink = this.value;
  selectedFile = null;
  const fileNameElem = document.getElementById("fileName");

  if (selectedLink && convertToEmbed(selectedLink)) {
    fileNameElem.textContent = "✓ YouTube link detected";
    fileNameElem.style.color = "#22c55e";
    showIFramePreview(convertToEmbed(selectedLink));
  } else if (selectedLink) {
    fileNameElem.textContent = "⚠ Invalid YouTube URL";
    fileNameElem.style.color = "#fbbf24";
  } else {
    fileNameElem.textContent = "";
  }
});

function showResultButtons() {
  submissionResult.textContent = "Comic created successfully!";
  submitButton.style.display = "none";
  resultButtons.style.display = "flex";
}

function previewComic() {
  window.open("/output/page.html", "_blank");
}

// 5. Submit button with progress tracking
function submitForm() {
  const submitBtn = document.getElementById("submitButton");
  const progressContainer = document.getElementById("progress-container");
  const progressBar = document.getElementById("progress-bar");
  const progressTextOverlay = document.getElementById("progress-text-overlay");
  const progressText = document.getElementById("progress-text");
  const resultButtons = document.getElementById("resultButtons");

  if (!selectedFile && selectedLink === "") {
    submissionResult.textContent =
      "⚠ Please upload a video or enter a YouTube link first";
    submissionResult.style.color = "#fbbf24";
    return;
  }

  submitBtn.textContent = "⏳ Generating...";
  submitBtn.disabled = true;
  submitBtn.style.opacity = "0.7";
  submissionResult.textContent = "";
  progressContainer.style.display = "block";
  progressBar.style.width = "0%";
  progressBar.style.background =
    "linear-gradient(90deg, #3b82f6 0%, #60a5fa 50%, #3b82f6 100%)";
  progressBar.style.backgroundSize = "200% 100%";
  progressTextOverlay.textContent = "0%";
  progressText.textContent = "🚀 Starting your comic generation...";
  progressText.style.color = "rgba(255, 255, 255, 0.8)";
  resultButtons.style.display = "none";

  const formdata = new FormData();
  if (selectedFile) {
    formdata.append("file", selectedFile);
  } else {
    formdata.append("link", selectedLink);
  }

  fetch("/start-job", { method: "POST", body: formdata })
    .then((response) => response.json())
    .then((data) => {
      if (data.job_id) {
        const source = new EventSource("/progress/" + data.job_id);

        source.onmessage = function (event) {
          const status = JSON.parse(event.data);

          progressBar.style.width = status.progress + "%";
          progressTextOverlay.textContent = status.progress + "%";
          progressText.textContent = status.message;

          if (status.progress >= 100) {
            progressBar.style.background =
              "linear-gradient(90deg, #22c55e 0%, #16a34a 100%)";
            progressBar.style.animation = "none";
            submitBtn.textContent = "Generate Comic";
            submitBtn.disabled = false;
            submitBtn.style.opacity = "1";
            progressText.textContent = "🎉 Your comic is ready!";
            progressText.style.color = "#22c55e";
            resultButtons.style.display = "flex";
            source.close();
          }

          if (status.progress === -1) {
            progressBar.style.background =
              "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)";
            progressBar.style.animation = "none";
            progressText.textContent =
              "❌ " + (status.message || "An error occurred");
            progressText.style.color = "#ef4444";
            submitBtn.textContent = "🔄 Try Again";
            submitBtn.disabled = false;
            submitBtn.style.opacity = "1";
            source.close();
          }
        };

        source.onerror = function (err) {
          console.error("EventSource failed:", err);
          progressText.textContent =
            "❌ Connection to server lost. Please try again.";
          progressText.style.color = "#ef4444";
          progressBar.style.background =
            "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)";
          progressBar.style.animation = "none";
          submitBtn.textContent = "🔄 Try Again";
          submitBtn.disabled = false;
          submitBtn.style.opacity = "1";
          source.close();
        };
      } else {
        throw new Error(data.error || "Failed to start job.");
      }
    })
    .catch((error) => {
      console.error("Error starting job:", error);
      progressText.textContent =
        "❌ Could not start the job. Please check your connection.";
      progressText.style.color = "#ef4444";
      progressBar.style.background =
        "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)";
      progressBar.style.animation = "none";
      progressContainer.style.display = "block";
      submitBtn.textContent = "🔄 Try Again";
      submitBtn.disabled = false;
      submitBtn.style.opacity = "1";
    });
}

// 6. Video preview
function showVideoPreview(url) {
  hideIFramePreview();
  videoPreview.src = url;
  videoPreview.style.display = "block";
  videoPreview.play();
  bgVideo.pause();
}

function hideVideoPreview() {
  videoPreview.src = "";
  videoPreview.style.display = "none";
  bgVideo.play();
}

function showIFramePreview(url) {
  hideVideoPreview();
  iFramePreview.src = url;
  iFramePreview.style.display = "block";
  bgVideo.pause();
}

function hideIFramePreview() {
  iFramePreview.src = "";
  iFramePreview.style.display = "none";
  bgVideo.play();
}
