
function onProvinceChange() {
    // 获取选中的省份
    const province = document.getElementById("province").value;

    // 发送异步请求到 Flask 后端
    fetch(`/get_city_list?province=${province}`)
        .then(response => response.json())  // 解析 JSON 数据
        .then(data => {
            const citySelect = document.getElementById("city");
            if (!citySelect) return;

            // 清空当前城市选项
            citySelect.innerHTML = "";

            // 根据返回的城市数据动态填充城市选项
            data.cities.forEach(city => {
                const option = document.createElement("option");
                option.value = city;
                option.textContent = city;
                citySelect.appendChild(option);
            });

            // 触发城市选项变更事件
            onCityChange();
        })
        .catch(error => console.error('Error:', error));
}

function onCityChange() {
    
    const province = document.getElementById("province").value;
    const city = document.getElementById("city").value;

    // 发送异步请求到 Flask 后端
    fetch(`/get_district_list?province=${province}&city=${city}`)
        .then(response => response.json())  // 解析 JSON 数据
        .then(data => {
            const districtSelect = document.getElementById("district");
            if (!districtSelect) return;

            // 清空当前区选项
            districtSelect.innerHTML = "";

            // 根据返回的区县数据动态填充选项
            data.districts.forEach(district => {
                const option = document.createElement("option");
                option.value = district;
                option.textContent = district;
                districtSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error:', error));
}
