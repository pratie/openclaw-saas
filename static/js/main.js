// Landing Page JavaScript

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    // Handle selector card clicks (models and channels)
    const selectorCards = document.querySelectorAll('.selector-card');
    selectorCards.forEach(card => {
        card.addEventListener('click', function() {
            // Don't select disabled options
            if (this.classList.contains('disabled')) {
                return;
            }

            // Get the radio input
            const radioInput = this.querySelector('input[type="radio"]');
            if (!radioInput) return;

            // Remove selected class from siblings with same name
            const radioName = radioInput.name;
            const siblings = document.querySelectorAll(`input[name="${radioName}"]`);
            siblings.forEach(sibling => {
                const parentCard = sibling.closest('.selector-card');
                if (parentCard) {
                    parentCard.classList.remove('selected');
                }
            });

            // Add selected class to this card
            this.classList.add('selected');
            radioInput.checked = true;
        });
    });
});
