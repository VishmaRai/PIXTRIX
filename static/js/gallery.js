
        // Matrix rain effect
        function createMatrixRain() {
            const matrixBg = document.querySelector('.matrix-bg');
            const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()_+-=[]{}|;:,.<>?';
            
            for (let i = 0; i < 50; i++) {
                const column = document.createElement('div');
                column.className = 'matrix-column';
                column.style.left = Math.random() * 100 + '%';
                column.style.animationDuration = (Math.random() * 3 + 2) + 's';
                column.style.animationDelay = Math.random() * 2 + 's';
                
                let text = '';
                for (let j = 0; j < 20; j++) {
                    text += characters.charAt(Math.floor(Math.random() * characters.length)) + '<br>';
                }
                column.innerHTML = text;
                
                matrixBg.appendChild(column);
            }
        }
        
        // Initialize matrix rain
        createMatrixRain();
        
        // Refresh matrix rain periodically
        setInterval(createMatrixRain, 10000);
        
        // Add glitch effect to title occasionally
        setInterval(() => {
            const title = document.querySelector('.title');
            title.style.textShadow = '2px 0 #ff0000, -2px 0 #00ffff';
            setTimeout(() => {
                title.style.textShadow = '0 0 20px #00FF00, 0 0 40px #00FF00';
            }, 100);
        }, 5000);
        
        // Add typewriter effect to prompt text
        document.querySelectorAll('.image-tile').forEach(tile => {
            const promptText = tile.querySelector('.prompt-text');
            const originalText = promptText.textContent;
            let typeInterval;

            tile.addEventListener('mouseenter', () => {
                promptText.textContent = ''; // Clear text before typing
                let i = 0;
                typeInterval = setInterval(() => {
                    if (i < originalText.length) {
                        promptText.textContent += originalText.charAt(i);
                        i++;
                    } else {
                        clearInterval(typeInterval);
                    }
                }, 5);
            });

            tile.addEventListener('mouseleave', () => {
                clearInterval(typeInterval); // Stop typing
                promptText.textContent = originalText; // Restore full text
            });
        });
