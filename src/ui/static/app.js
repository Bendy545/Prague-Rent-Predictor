document.getElementById('predictBtn').addEventListener('click', async () => {
    const data = {
        size_m2: document.getElementById('size_m2').value,
        room_count: document.getElementById('room_count').value,
        floor_number: document.getElementById('floor_number').value,
        district: document.getElementById('district').value,
        building_type: document.getElementById('building_type').value,
        condition: document.getElementById('condition').value,
        ownership: document.getElementById('ownership').value,
        furnished: document.getElementById('furnished').value,
        elevator: document.getElementById('elevator').value,
        has_separate_kitchen: document.getElementById('has_separate_kitchen').checked ? 1 : 0,
        has_balcony: document.getElementById('has_balcony').checked ? 1 : 0,
        has_terrace: document.getElementById('has_terrace').checked ? 1 : 0,
        has_cellar: document.getElementById('has_cellar').checked ? 1 : 0,
        has_parking: document.getElementById('has_parking').checked ? 1 : 0,
    };

    const response = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });

    const result = await response.json();

    const resultCard = document.getElementById('resultCard');
    const resultPrice = document.getElementById('resultPrice');

    resultPrice.textContent = Number(result.price).toLocaleString('cs-CZ');
    resultCard.style.display = 'block';
    resultCard.scrollIntoView({ behavior: 'smooth' });
});