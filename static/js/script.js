// State management
let currentJobId = null;
let progressInterval = null;
let loraData = {
    fast: [],
    slow: []
};

// DOM Elements
const modelTypeInputs = document.querySelectorAll('input[name="model"]');
const fastLoraGroup = document.getElementById('fast_loras');
const slowLoraGroup = document.getElementById('slow_loras');
const fastLoraCheckboxes = document.getElementById('fastLoraCheckboxes');
const slowLoraCheckboxes = document.getElementById('slowLoraCheckboxes');
const generateBtn = document.getElementById('generateBtn');
const progressContainer = document.getElementById('progressContainer');
const progressBarFill = document.querySelector('.progress-bar-fill');
const progressPercentage = document.querySelector('.progress-percentage');
const imageGrid = document.getElementById('imageGrid');
const imageModal = document.getElementById('imageModal');
const modalImage = document.getElementById('modalImage');
const closeModal = document.querySelector('.close-modal');

// Fetch and populate LoRA data
async function fetchLoraData() {
    try {
        const response = await fetch('/api/loras');
        const data = await response.json();
        loraData = data;
        updateLoraCheckboxes();
    } catch (error) {
        console.error('Error fetching LoRA data:', error);
    }
}

// Create checkbox element for a LoRA
function createLoraCheckbox(lora) {
    const label = document.createElement('label');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = lora.id;
    checkbox.name = 'lora';
    const text = document.createTextNode(lora.name);
    
    label.appendChild(checkbox);
    label.appendChild(text);
    
    return label;
}

// Update LoRA checkboxes based on model type
function updateLoraCheckboxes() {
    // Clear existing checkboxes
    fastLoraCheckboxes.innerHTML = '';
    slowLoraCheckboxes.innerHTML = '';
    
    // Add fast model LoRAs
    loraData.fast.forEach(lora => {
        const checkbox = createLoraCheckbox(lora);
        fastLoraCheckboxes.appendChild(checkbox);
    });
    
    // Add slow model LoRAs
    loraData.slow.forEach(lora => {
        const checkbox = createLoraCheckbox(lora);
        slowLoraCheckboxes.appendChild(checkbox);
    });
}

// Toggle LoRA groups based on model selection
function toggleLoraGroups(modelType) {
    if (modelType === 'fast') {
        fastLoraGroup.classList.add('active');
        slowLoraGroup.classList.remove('active');
    } else {
        fastLoraGroup.classList.remove('active');
        slowLoraGroup.classList.add('active');
    }
}

// Generate image
async function generateImage() {
    const prompt = document.getElementById('prompt').value;
    const aspectRatio = document.querySelector('input[name="aspect"]:checked').value;
    const modelType = document.querySelector('input[name="model"]:checked').value;
    const activeLoraGroup = modelType === 'fast' ? fastLoraCheckboxes : slowLoraCheckboxes;
    const selectedLoras = Array.from(activeLoraGroup.querySelectorAll('input:checked')).map(input => input.value);
    
    if (!prompt.trim()) {
        alert('Please enter a prompt');
        return;
    }

    // Show progress
    progressContainer.classList.remove('hidden');
    generateBtn.disabled = true;

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt,
                aspectRatio,
                modelType,
                loras: selectedLoras
            })
        });

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        currentJobId = data.jobId;
        startProgressPolling();

    } catch (error) {
        alert('Error generating image: ' + error.message);
        progressContainer.classList.add('hidden');
        generateBtn.disabled = false;
    }
}

// Poll for generation progress
function startProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }

    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentJobId}`);
            const data = await response.json();

            progressBarFill.style.width = `${data.progress}%`;
            progressPercentage.textContent = `${data.progress}%`;

            if (data.status === 'completed' && data.imageUrl) {
                clearInterval(progressInterval);
                addImageToGallery(data.imageUrl);
                progressContainer.classList.add('hidden');
                generateBtn.disabled = false;
                currentJobId = null;
            } else if (data.status === 'failed') {
                clearInterval(progressInterval);
                alert('Image generation failed');
                progressContainer.classList.add('hidden');
                generateBtn.disabled = false;
                currentJobId = null;
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 1000);
}

// Add generated image to gallery
function addImageToGallery(imageUrl) {
    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = 'Generated image';
    img.addEventListener('click', () => showModal(imageUrl));
    imageGrid.insertBefore(img, imageGrid.firstChild);
}

// Load existing images
async function loadExistingImages() {
    try {
        const response = await fetch('/api/images');
        const imageUrls = await response.json();
        
        imageUrls.forEach(imageUrl => {
            const img = document.createElement('img');
            img.src = imageUrl;
            img.alt = 'Generated image';
            img.addEventListener('click', () => showModal(imageUrl));
            imageGrid.appendChild(img);
        });
    } catch (error) {
        console.error('Error loading existing images:', error);
    }
}

// Modal functions
function showModal(imageSrc) {
    modalImage.src = imageSrc;
    imageModal.classList.add('active');
}

function hideModal() {
    imageModal.classList.remove('active');
}

// Event Listeners
modelTypeInputs.forEach(input => {
    input.addEventListener('change', (e) => toggleLoraGroups(e.target.value));
});

generateBtn.addEventListener('click', generateImage);
closeModal.addEventListener('click', hideModal);
imageModal.addEventListener('click', (e) => {
    if (e.target === imageModal) hideModal();
});

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    fetchLoraData(); // Fetch LoRA data on page load
    toggleLoraGroups(document.querySelector('input[name="model"]:checked').value);
    loadExistingImages();
});
