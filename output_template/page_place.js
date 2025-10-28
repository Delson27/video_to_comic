path = "../frames/final/";
current_page = 0;

function placeDialogs(page) {
  var gridContainer = document.querySelector(".grid-container");
  var gridItems = document.querySelectorAll(".grid-item");

  // ✅ Remove all existing classes
  gridContainer.classList.remove(
    "squares",
    "last-page-1",
    "last-page-2",
    "last-page-3",
    "last-page-4",
    "last-page-5",
    "last-page-6",
    "last-page-7"
  );

  // ✅ Apply appropriate grid style based on panel count
  if (page.panels.length == 8) {
    // Normal page - 8 panels, all squares
    gridContainer.classList.add("squares");
  } else {
    // Last page - smart layout based on panel count
    gridContainer.classList.add("last-page-" + page.panels.length);
  }

  page.panels.forEach(function (panel, index) {
    var gridItem = gridItems[index];

    gridItem.style.display = "flex";
    gridItem.style.gridRow = "span " + panel.row_span;
    gridItem.style.gridColumn = "span " + panel.col_span;

    // ✅ REMOVED background image - using <img> element instead
    // gridItem.style.backgroundImage = `url("${path}${panel.image}.png")`;

    gridItem.innerHTML = ""; // Clear previous content

    // ✅ NEW: Create actual <img> element for better control
    const imgElement = document.createElement("img");
    imgElement.src = `${path}${panel.image}.png`;
    imgElement.style.width = "100%";
    imgElement.style.height = "100%";
    imgElement.style.objectFit = "contain"; // Fills panel, crops edges if needed
    imgElement.style.objectPosition = "center center"; // Centers the image
    imgElement.style.position = "absolute";
    imgElement.style.top = "0";
    imgElement.style.left = "0";
    gridItem.appendChild(imgElement);

    const dialog_temp = page["bubbles"][index]["dialog"];

    if (dialog_temp != "((action-scene))") {
      const wrapper = document.createElement("div");
      wrapper.style.position = "absolute"; // ✅ Changed from relative to absolute
      wrapper.style.top = "0";
      wrapper.style.left = "0";
      wrapper.style.width = "100%";
      wrapper.style.height = "100%";
      wrapper.style.overflow = "visible"; // ✅ CHANGED: Allow bubbles to be fully visible
      wrapper.style.pointerEvents = "none"; // Allow clicking through wrapper
      wrapper.style.zIndex = "10"; // ✅ Ensure bubbles appear above panels

      const bubble_temp = document.createElement("div");
      bubble_temp.classList.add("bubble");
      bubble_temp.innerHTML = page["bubbles"][index]["dialog"];
      bubble_temp.style.pointerEvents = "auto"; // Re-enable pointer events on bubble

      const emotion = page["bubbles"][index]["emotion"];

      // ✅ FIX: Use rounded coordinates for consistent placement
      const bubble_x = Math.round(page["bubbles"][index]["bubble_offset_x"]);
      const bubble_y = Math.round(page["bubbles"][index]["bubble_offset_y"]);

      if (emotion == "jagged") {
        bubble_temp.style.backgroundImage = `url("assets/jagged.png")`;
        bubble_temp.style.backgroundPosition = "center center";
        bubble_temp.style.backgroundRepeat = "no-repeat";
        bubble_temp.style.backgroundSize = "cover";
        bubble_temp.style.backgroundColor = "transparent";
        bubble_temp.style.width = "200px";
        bubble_temp.style.height = "94px";
        bubble_temp.style.padding = "70px";
        // ✅ FIX: Consistent 2px border for jagged bubbles
        bubble_temp.style.border = "none"; // Jagged style has custom border
      } else {
        // ✅ FIX: Consistent styling for normal bubbles
        bubble_temp.style.border = "2px solid black";
        bubble_temp.style.backgroundColor = "white";
      }

      bubble_temp.style.fontSize = "10px"; // ✅ FIX: Fixed font size instead of dialog length
      bubble_temp.style.transform = `translate(${bubble_x}px, ${bubble_y}px)`; // ✅ FIX: Use rounded coords

      const tail = document.createElement("div");
      tail.classList.add("tail");
      if (
        page["bubbles"][index]["tail_offset_x"] == null ||
        emotion == "jagged"
      ) {
        tail.style.display = "none";
      } else {
        // ✅ FIX: Use rounded coordinates for tail offset
        const tail_x = Math.round(page["bubbles"][index]["tail_offset_x"]);
        const tail_y = Math.round(page["bubbles"][index]["tail_offset_y"]);
        tail.style.transform = `translate(${tail_x}px, ${tail_y}px) rotate(${page["bubbles"][index]["tail_deg"]}deg)`;
      }

      bubble_temp.appendChild(tail);
      wrapper.appendChild(bubble_temp);
      gridItem.appendChild(wrapper); // Append the wrapper to the grid item
    }
  });

  for (var i = page.panels.length; i < gridItems.length; i++) {
    gridItems[i].style.display = "none";
  }
}

function updateNavigationButtons() {
  // Get navigation buttons
  const prevButtons = document.querySelectorAll('button[onclick="prevPage()"]');
  const nextButtons = document.querySelectorAll('button[onclick="nextPage()"]');

  // Update previous button state
  prevButtons.forEach((button) => {
    if (current_page === 0) {
      // First page - disable previous button
      button.disabled = true;
      button.style.opacity = "0.3";
      button.style.cursor = "not-allowed";
    } else {
      // Not first page - enable previous button
      button.disabled = false;
      button.style.opacity = "1";
      button.style.cursor = "pointer";
    }
  });

  // Update next button state
  nextButtons.forEach((button) => {
    if (current_page === pages.length - 1) {
      // Last page - disable next button
      button.disabled = true;
      button.style.opacity = "0.3";
      button.style.cursor = "not-allowed";
    } else {
      // Not last page - enable next button
      button.disabled = false;
      button.style.opacity = "1";
      button.style.cursor = "pointer";
    }
  });
}

document.addEventListener("DOMContentLoaded", function () {
  console.log("Total pages:", pages.length);
  console.log("Current page:", current_page + 1);
  placeDialogs(pages[current_page]);
  updateNavigationButtons(); // Update button states on initial load
});

function prevPage() {
  // Prevent navigation if already on first page
  if (current_page === 0) {
    console.log("Already on first page");
    return;
  }

  current_page = current_page - 1;
  console.log("Previous page:", current_page + 1);
  placeDialogs(pages[current_page]);
  updateNavigationButtons(); // Update button states after navigation
}

function nextPage() {
  // Prevent navigation if already on last page
  if (current_page === pages.length - 1) {
    console.log("Already on last page");
    return;
  }

  current_page = current_page + 1;
  console.log("Next page:", current_page + 1);
  placeDialogs(pages[current_page]);
  updateNavigationButtons(); // Update button states after navigation
}

function sendPageDataToBackend(page) {
  fetch("/generate-pdf", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(page),
  })
    .then((response) => {
      if (response.ok) {
        console.log("Page data sent successfully");
      } else {
        console.error("Failed to send page data");
      }
    })
    .catch((error) => {
      console.error("Error sending page data:", error);
    });
}

// Example usage
// sendPageDataToBackend(currentPageData);
