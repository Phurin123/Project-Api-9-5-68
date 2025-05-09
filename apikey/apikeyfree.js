function generateApiKey() {
    // ดึงอีเมลจาก sessionStorage
    let email = sessionStorage.getItem('userEmail');

    // ตรวจสอบว่ามีอีเมลหรือไม่
    if (!email) {
        alert("กรุณาล็อกอินก่อน");
        return;
    }

    // รับข้อมูลจาก checkbox สำหรับประเภทการวิเคราะห์
    let analysisTypes = [];
    let thresholds = {};  // เก็บค่า threshold สำหรับแต่ละประเภท
    document.querySelectorAll('.analysis-option:checked').forEach(option => {
        analysisTypes.push(option.value);
        // รับค่า threshold จาก slider สำหรับแต่ละประเภท
        let threshold = document.getElementById(option.value + '-threshold').value;
        thresholds[option.value] = parseFloat(threshold);
    });

    // รับค่าจำนวน quota จาก input
    let quota = document.getElementById("quota").value;

    // ตรวจสอบว่ามีการเลือกประเภทการวิเคราะห์หรือไม่
    if (analysisTypes.length === 0) {
        alert("กรุณากรอกข้อมูลทั้งหมด");
        return;
    }

    // ส่งข้อมูลไปที่ back-end
    fetch('http://localhost:5000/request-api-key', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: email,
            analysis_types: analysisTypes,
            thresholds: thresholds,  // ส่งค่า threshold ไปพร้อมกับประเภทการวิเคราะห์
            quota: quota,
            plan: 'free'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else if (data.apiKey) {
            document.getElementById("apiKey").textContent = data.apiKey;
        } else {
            alert("เกิดข้อผิดพลาดในการสร้าง API Key");
        }
    })
    .catch(error => {
        console.error("เกิดข้อผิดพลาดในการเชื่อมต่อ:", error);
        alert("เกิดข้อผิดพลาดในการเชื่อมต่อกับ server");
    });
}
