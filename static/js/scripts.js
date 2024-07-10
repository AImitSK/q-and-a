document.getElementById('uploadForm').onsubmit = async function(event) {
    event.preventDefault();
    const formData = new FormData();
    formData.append('pdfFile', document.getElementById('pdfFile').files[0]);
    const response = await fetch('/upload', {
        method: 'POST',
        body: formData
    });
    if (response.ok) {
        document.getElementById('qaSection').style.display = 'block';
    } else {
        console.error('Upload failed');
    }
};

document.getElementById('askButton').onclick = async function() {
    const question = document.getElementById('questionInput').value;
    const response = await fetch('/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question })
    });
    const data = await response.json();
    document.getElementById('answer').innerText = data.answer;
};
