// รับ email จาก URL ถ้ามี
const urlParams = new URLSearchParams(window.location.search);
const emailFromURL = urlParams.get('email');

// ถ้ายังไม่มี email ใน sessionStorage แต่มีใน URL ให้เก็บไว้
if (emailFromURL && !sessionStorage.getItem('userEmail')) {
    sessionStorage.setItem('userEmail', emailFromURL);
}

// ฟังก์ชันในการดึงชื่อผู้ใช้
async function fetchUsername(email) {
    try {
        const res = await fetch(`http://localhost:5000/get-username?email=${email}`);
        const data = await res.json();

        if (res.ok && data.username) {
            document.getElementById("usernameDisplay").textContent = `👤 สวัสดีคุณ: ${data.username}`;
        } else {
            document.getElementById("usernameDisplay").textContent = `👤 Logged in as: ${email}`;
        }
    } catch (err) {
        console.error("Error fetching username:", err);
        document.getElementById("usernameDisplay").textContent = `👤 Logged in as: ${email}`;
    }
}

// ฟังก์ชันในการดึงข้อมูล API Keys ของผู้ใช้
// ฟังก์ชันในการดึงข้อมูล API Keys ของผู้ใช้
function fetchApiKeys() {
    const email = sessionStorage.getItem('userEmail');

    if (!email) {
        document.getElementById("apiKeysList").innerHTML = "<p>กรุณาเข้าสู่ระบบก่อน</p>";
        return;
    }

    fetch(`http://localhost:5000/get-api-keys?email=${email}`)  // เปลี่ยน URL เมื่อนำไป deploy
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById("apiKeysList").innerHTML = `<p>${data.error}</p>`;
            } else {
                let apiKeysHtml = "";
                data.api_keys.forEach(key => {
                    apiKeysHtml += `
                        <div class="api-key">
                            <p><strong>Email:</strong> ${email}</p>
                            <p><strong>API Key:</strong> ${key.api_key}</p>
                            <p><strong>Analysis Types:</strong> ${key.analysis_types.join(", ")}</p>
                            <p><strong>Quota:</strong> ${key.quota}</p>
                            <p><strong>Threshold:</strong> ${Object.entries(key.thresholds).map(([type, val]) => `${type}: ${val}`).join(", ")}</p>
                        </div>
                    `;
                });
                document.getElementById("apiKeysList").innerHTML = apiKeysHtml;
            }
        })
        .catch(error => {
            console.error("Error fetching API keys:", error);
            document.getElementById("apiKeysList").innerHTML = "<p>เกิดข้อผิดพลาดในการดึงข้อมูล API Keys</p>";
        });
}


// โหลดข้อมูลเมื่อเปิดหน้า
window.onload = async function () {
    const email = sessionStorage.getItem('userEmail');
    if (!email) {
        document.getElementById("usernameDisplay").textContent = "⚠️ กรุณาเข้าสู่ระบบ";
        return;
    }

    await fetchUsername(email);
    fetchApiKeys();
};
