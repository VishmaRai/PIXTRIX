// Global variables
let isGenerating = false;

// Matrix rain generator for image slots
function createMatrixRain(container) {
  container.innerHTML = '';
  const columns = Math.floor(container.offsetWidth / 14);
  
  for (let i = 0; i < columns; i++) {
    const col = document.createElement('div');
    col.className = 'rain-column';
    col.style.left = `${(i * 14)}px`;
    col.style.animationDuration = `${Math.random() * 2 + 1}s`;
    container.appendChild(col);
    
    // Create characters
    const charCount = Math.floor(container.offsetHeight / 14);
    for (let j = 0; j < charCount; j++) {
      const char = document.createElement('span');
      char.textContent = String.fromCharCode(0x30A0 + Math.random() * 96);
      char.style.opacity = Math.random();
      char.style.animationDelay = `${Math.random() * 2}s`;
      col.appendChild(char);
    }
  }
}

// Reset form to initial state
function resetFormState() {
  isGenerating = false;
  
  const generateBtn = document.querySelector('.generate-btn');
  const promptArea = document.querySelector('.prompt-area');
  const aspectSelector = document.getElementById('aspectSelector');
  
  if (generateBtn) {
    generateBtn.disabled = false;
    generateBtn.innerHTML = '<i class="fas fa-bolt" style="margin-right: 10px"></i> Generate';
  }
  
  if (promptArea) {
    promptArea.readOnly = false;
    promptArea.style.cursor = 'text';
  }
  
  if (aspectSelector) aspectSelector.classList.remove('disabled');
}

// Update image slot with new image
function updateImageSlot(slotNum, img) {
  const slot = document.getElementById(`slot${slotNum}`);
  const overlay = document.getElementById(`overlay${slotNum}`);
  const placeholder = slot.querySelector('.image-placeholder');
  
  if (slot && overlay && placeholder) {
    // Create image element if it doesn't exist
    let imgElement = slot.querySelector('img');
    if (!imgElement) {
      imgElement = document.createElement('img');
      imgElement.style.display = 'none';
      slot.appendChild(imgElement);
    }
    
    // Create download button if it doesn't exist
    let downloadBtn = slot.querySelector('.download-btn');
    if (!downloadBtn) {
      downloadBtn = document.createElement('a');
      downloadBtn.className = 'download-btn';
      downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download';
      slot.appendChild(downloadBtn);
    }
    
    // Update elements
    imgElement.src = img;
    imgElement.alt = `Generated image ${slotNum}`;
    imgElement.style.display = 'block';
    
    downloadBtn.href = img;
    downloadBtn.download = `pixtrix_${slotNum}.png`;
    downloadBtn.style.display = 'block';
    
    placeholder.style.display = 'none';
    overlay.style.display = 'none';
    slot.classList.add('has-image');
  }
}

// Reset image slots for new generation
function resetImageSlots() {
  for (let i = 1; i <= 2; i++) {
    const slot = document.getElementById(`slot${i}`);
    const overlay = document.getElementById(`overlay${i}`);
    const placeholder = slot.querySelector('.image-placeholder');
    const img = slot.querySelector('img');
    const downloadBtn = slot.querySelector('.download-btn');
    
    if (slot && overlay && placeholder) {
      // Hide image and download button
      if (img) img.style.display = 'none';
      if (downloadBtn) downloadBtn.style.display = 'none';
      
      // Show placeholder
      placeholder.style.display = 'block';
      
      // Reset overlay
      overlay.style.display = 'none';
      slot.classList.remove('has-image');
    }
  }
}

// Custom Alert Function
function showMatrixAlert(message, onOk) {
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'matrix-alert-overlay';

    // Create alert box
    const alertBox = document.createElement('div');
    alertBox.className = 'matrix-alert-box';

    // Create message element
    const messageEl = document.createElement('p');
    messageEl.className = 'matrix-alert-message';
    messageEl.textContent = message;

    // Create OK button
    const okButton = document.createElement('button');
    okButton.className = 'matrix-alert-button';
    okButton.textContent = 'OK';

    // Append elements
    alertBox.appendChild(messageEl);
    alertBox.appendChild(okButton);
    overlay.appendChild(alertBox);
    document.body.appendChild(overlay);

    // Show the alert with animation
    setTimeout(() => {
        overlay.style.opacity = '1';
        alertBox.style.transform = 'scale(1)';
    }, 10);

    // Handle button click
    okButton.addEventListener('click', () => {
        overlay.style.opacity = '0';
        alertBox.style.transform = 'scale(0.9)';
        setTimeout(() => {
            document.body.removeChild(overlay);
            if (onOk) onOk();
        }, 300);
    });
}

// Form submission handler
async function handleFormSubmit(e) {
  e.preventDefault();
  if (isGenerating) return;

  const creditCountEl = document.getElementById('creditCount');
  let currentCredits = parseInt(creditCountEl.textContent.trim());

  if (currentCredits <= 0) {
    showMatrixAlert("You have used all your free generations. Please log in to continue.", () => {
      window.location.href = '/login';
    });
    return;
  }

  isGenerating = true;

  // Optimistically decrement credits
  creditCountEl.innerHTML = `<i class="fas fa-bolt"></i> ${currentCredits - 1}`;

  // Disable form elements
  const form = document.getElementById('imageForm');
  const generateBtn = document.querySelector('.generate-btn');
  const promptArea = document.querySelector('.prompt-area');
  const aspectSelector = document.getElementById('aspectSelector');

  // Update button to show loading state
  generateBtn.disabled = true;
  generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right: 5px;"></i> Generating..';

  // Reset slots for new generation
  resetImageSlots();
  // Show overlays on both slots
  document.getElementById('overlay1').style.display = 'flex';
  document.getElementById('overlay2').style.display = 'flex';
  // Create matrix rain effects
  createMatrixRain(document.getElementById('matrixRain1'));
  createMatrixRain(document.getElementById('matrixRain2'));

  // Prepare form data
  const formData = new FormData(form);
  try {
    // Send AJAX request
    const response = await fetch('/', {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData
    });
    
    const data = await response.json();

    if (!response.ok) {
      // Revert credit count on failure
      creditCountEl.innerHTML = `<i class="fas fa-bolt"></i> ${currentCredits}`;
      if (data.error) {
        showMatrixAlert(data.error, () => {
          if (response.status === 403 && data.error.includes("Please log in")) {
            window.location.href = '/login';
          }
        });
      } else {
        showMatrixAlert('An unknown error occurred.');
      }
    } else {
      // Update images
      if (data.images && data.images.length > 0) {
        if (data.images[0]) { updateImageSlot(1, data.images[0]); }
        if (data.images[1]) { updateImageSlot(2, data.images[1]); }
      }
    }
  } catch (e) {
    // Revert credit count on failure
    creditCountEl.innerHTML = `<i class="fas fa-bolt"></i> ${currentCredits}`;
    console.error('Image generation failed:', e);
    showMatrixAlert('An error occurred while generating images.');
  } finally {
    // Re-enable form elements
    resetFormState();
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function() {
  // Glitch effect on logo
  setInterval(() => {
    const logo = document.querySelector(".logo");
    logo.style.animation = "none";
    setTimeout(() => {
      logo.style.animation = "glow 2s ease-in-out infinite alternate";
    }, 100);
  }, 5000);

  // Aspect ratio selector functionality
  const aspectSelector = document.getElementById("aspectSelector");
  const aspectValue = aspectSelector.querySelector(".aspect-select-value");
  const aspectOptions = aspectSelector.querySelectorAll(".aspect-option");

  // Toggle options visibility
  aspectSelector.addEventListener("click", function(e) {
    if (this.classList.contains('disabled')) return;
    this.classList.toggle("active");
  });

  // Handle option selection
  aspectOptions.forEach((option) => {
    option.addEventListener("click", function() {
      // Update selected state
      aspectOptions.forEach((opt) => opt.classList.remove("selected"));
      this.classList.add("selected");

      // Update displayed value
      aspectValue.textContent = this.textContent;

      // Update hidden input value
      document.getElementById("aspectInput").value =
        this.getAttribute("data-value");
    });
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", function(e) {
    if (!aspectSelector.contains(e.target)) {
      aspectSelector.classList.remove("active");
    }
  });

  // Matrix Rain Canvas Animation (background)
  var canvas = document.getElementById('matrix-canvas'),
      ctx = canvas.getContext('2d');
  var fontSize = 18;
  var letters = 'ABCDEFGHIJKLMNOPQRSTUVXYZABCDEFGHIJKLMNOPQRSTUVXYZABCDEFGHIJKLMNOPQRSTUVXYZABCDEFGHIJKLMNOPQRSTUVXYZABCDEFGHIJKLMNOPQRSTUVXYZABCDEFGHIJKLMNOPQRSTUVXYZ'.split('');
  var columns, drops;
  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    columns = Math.floor(canvas.width / fontSize);
    drops = [];
    for (var i = 0; i < columns; i++) drops[i] = 1;
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();
  function drawMatrixRain() {
    ctx.fillStyle = 'rgba(0, 0, 0, .1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = fontSize + "px 'Courier Prime', monospace";
    for (var i = 0; i < drops.length; i++) {
      var text = letters[Math.floor(Math.random() * letters.length)];
      ctx.fillStyle = '#00ff41';
      ctx.fillText(text, i * fontSize, drops[i] * fontSize);
      drops[i]++;
      if (drops[i] * fontSize > canvas.height && Math.random() > .95) {
        drops[i] = 0;
      }
    }
  }
  setInterval(drawMatrixRain, 33);

  // Form submission handler
  document.getElementById('imageForm').addEventListener('submit', handleFormSubmit);

  const creditCount = document.getElementById('creditCount');

  creditCount.addEventListener('mouseenter', () => {
    const currentCredits = parseInt(creditCount.textContent.match(/\d+/)[0]);
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.innerHTML = `<span class="tooltip-text">You have ${currentCredits} credits left.</span>`;
    creditCount.appendChild(tooltip);
    tooltip.style.display = 'block';
  });

  creditCount.addEventListener('mouseleave', () => {
    const tooltip = creditCount.querySelector('.tooltip');
    if (tooltip) {
      tooltip.remove();
    }
  });
});
