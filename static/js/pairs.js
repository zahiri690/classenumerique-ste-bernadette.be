function onDragStart(event) {
    event.dataTransfer.setData('text/plain', event.target.dataset.index);
    event.target.classList.add('dragging');
}

function onDragOver(event) {
    event.preventDefault();
    event.target.closest('.drop-zone').classList.add('drag-over');
}

function onDragLeave(event) {
    event.target.closest('.drop-zone').classList.remove('drag-over');
}

function onDrop(event) {
    event.preventDefault();
    const dropZone = event.target.closest('.drop-zone');
    dropZone.classList.remove('drag-over');
    
    const draggedIndex = event.dataTransfer.getData('text/plain');
    const targetIndex = dropZone.dataset.index;
    
    // Update the hidden input with the pair
    const input = dropZone.querySelector('input[type="hidden"]');
    input.value = draggedIndex;
    
    // Update visual feedback
    const selectedItem = document.querySelector(`#leftItems .list-group-item[data-index="${draggedIndex}"]`);
    dropZone.querySelector('.selected-item').textContent = selectedItem.textContent;
    dropZone.classList.add('has-item');
    
    // Remove dragging class from source element
    document.querySelector('.dragging').classList.remove('dragging');
}

// Add drag leave event listener to all drop zones
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.drop-zone').forEach(zone => {
        zone.addEventListener('dragleave', onDragLeave);
    });
});
