document.addEventListener('DOMContentLoaded', function() {
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadStatus = document.getElementById('uploadStatus');
    const receiptImage = document.getElementById('receiptImage');

    if (uploadBtn && uploadStatus && receiptImage) {
        uploadBtn.addEventListener('click', function() {
            const file = receiptImage.files[0];
            if (!file) {
                uploadStatus.textContent = 'กรุณาเลือกไฟล์ใบเสร็จ';
                return;
            }

            // สร้าง FormData สำหรับส่งไฟล์
            const formData = new FormData();
            formData.append('receipt', file);

            // ส่งไฟล์ไปยังเซิร์ฟเวอร์
            fetch('http://localhost:5000/upload-receipt', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    uploadStatus.textContent = 'อัปโหลดสำเร็จ! API Key: ' + data.api_key;
                } else {
                    uploadStatus.textContent = 'เกิดข้อผิดพลาด: ' + data.error;
                }
            })
            .catch(error => {
                uploadStatus.textContent = 'เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์';
            });
        });
    }
});
