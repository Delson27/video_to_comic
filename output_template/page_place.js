path = '../frames/final/'
current_page = 0

function placeDialogs(page) {
    var gridContainer = document.querySelector('.grid-container');
    var gridItems = document.querySelectorAll('.grid-item');
    
    // ✅ Remove all existing classes
    gridContainer.classList.remove('squares', 'last-page-1', 'last-page-2', 'last-page-3', 
                                   'last-page-4', 'last-page-5', 'last-page-6', 'last-page-7');
    
    // ✅ Apply appropriate grid style based on panel count
    if (page.panels.length == 8) {
        // Normal page - 8 panels, all squares
        gridContainer.classList.add('squares');
    } else {
        // Last page - smart layout based on panel count
        gridContainer.classList.add('last-page-' + page.panels.length);
    }

    page.panels.forEach(function (panel, index) {
        var gridItem = gridItems[index];

        gridItem.style.display = 'flex';
        gridItem.style.gridRow = 'span ' + panel.row_span;
        gridItem.style.gridColumn = 'span ' + panel.col_span;
        gridItem.style.backgroundImage = `url("${path}${panel.image}.png")`;

        gridItem.innerHTML = "";

        const dialog_temp = page['bubbles'][index]['dialog'];

        if(dialog_temp != "((action-scene))"){

            const wrapper = document.createElement('div');
            wrapper.style.position = 'relative'; // Wrapper to contain the bubble
            wrapper.style.width = '100%';
            wrapper.style.height = '100%';

            const bubble_temp = document.createElement('div');
            bubble_temp.classList.add('bubble');
            bubble_temp.innerHTML = page['bubbles'][index]['dialog'];

            const emotion = page['bubbles'][index]['emotion'];

            if (emotion == 'jagged') {
                bubble_temp.style.backgroundImage = `url("assets/jagged.png")`;
                bubble_temp.style.backgroundPosition = 'center center';
                bubble_temp.style.backgroundRepeat = 'no-repeat';
                bubble_temp.style.backgroundSize = 'cover';
                bubble_temp.style.backgroundColor = 'transparent';
                bubble_temp.style.width = '200px'; // Adjust height if necessary
                bubble_temp.style.height = '94px'; // Adjust height if necessary
                bubble_temp.style.padding = '70px'; // Adjust height if necessary

            }

            bubble_temp.style.fontSize = dialog_temp.length;
            bubble_temp.style.transform = `translate(${page['bubbles'][index]['bubble_offset_x']}px, ${page['bubbles'][index]['bubble_offset_y']}px)`;

            const tail = document.createElement('div');
            tail.classList.add('tail');
            if (page['bubbles'][index]['tail_offset_x'] == null || emotion == 'jagged') {
                tail.style.display = 'none';
            } else {
                tail.style.transform = `translate(${page['bubbles'][index]['tail_offset_x']}px, ${page['bubbles'][index]['tail_offset_y']}px) rotate(${page['bubbles'][index]['tail_deg']}deg)`;
            }

            bubble_temp.appendChild(tail);
            wrapper.appendChild(bubble_temp);
            gridItem.appendChild(wrapper); // Append the wrapper to the grid item

        }
    });

    for (var i = page.panels.length; i < gridItems.length; i++) {
        gridItems[i].style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Total pages:', pages.length);
    console.log('Current page:', current_page + 1);
    placeDialogs(pages[current_page]);
});

function prevPage(){
    current_page = (current_page - 1);
    if(current_page < 0){
        current_page = pages.length - 1;
    }
    console.log('Previous page:', current_page + 1);
    placeDialogs(pages[current_page]);
}

function nextPage(){
    current_page = (current_page + 1) % pages.length;
    console.log('Next page:', current_page + 1);
    placeDialogs(pages[current_page]);
}

