def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    # options.add_argument('--headless')  # Раскомментируйте для скрытого режима

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"Ошибка инициализации драйвера: {e}")
        return None


def get_hotel_address(driver):
    address_selectors = [
        '//div[@data-marker="seller-address/address"]',
        '//span[@itemprop="streetAddress"]',
        '//div[contains(@class, "style-item-address")]',
        '//div[contains(text(), "Адрес:")]/following-sibling::div',
        '//div[contains(@class, "location-value")]'
    ]

    for selector in address_selectors:
        try:
            element = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.XPATH, selector)))
            address = element.text.strip()
            if address and len(address) > 5:
                return address
        except:
            continue

    return "Адрес не указан"


def parse_hotels(driver, city, max_results=5):
    base_url = f"https://www.avito.ru/{city}/predlozheniya_uslug/domashniy_personalgostinicy-ASgBAgICAUSYA9IV?q=гостиница"
    driver.get(base_url)
    time.sleep(3)

    results = []
    seen_links = set()

    while len(results) < max_results:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        items = driver.find_elements(By.XPATH, '//div[@data-marker="item"]')

        for item in items[len(results):max_results]:
            try:
                link_element = item.find_element(By.XPATH, './/a[@data-marker="item-title"]')
                link = link_element.get_attribute('href')

                if link in seen_links:
                    continue
                seen_links.add(link)

                title = link_element.text.strip()

                # Переходим на страницу объявления
                driver.execute_script(f"window.open('{link}', '_blank');")
                driver.switch_to.window(driver.window_handles[1])
                time.sleep(2)

                # Получаем адрес
                address = get_hotel_address(driver)

                results.append({
                    'title': title,
                    'address': address,
                    'link': link
                })

                # Закрываем вкладку и возвращаемся
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

                if len(results) >= max_results:
                    break

            except Exception as e:
                print(f"Ошибка при обработке объявления: {e}")
                continue

    return results


if name == "main":
    city = "krasnodar"  # Можно изменить на другой город
    max_results = 5

    driver = setup_driver()
    if not driver:
        print("Не удалось инициализировать ChromeDriver")
        exit()

    try:
        hotels = parse_hotels(driver, city, max_results)

        print("\n=== Найденные гостиницы ===")
        for i, hotel in enumerate(hotels, 1):
            print(f"{i}. {hotel['title']}")
            print(f"   Адрес: {hotel['address']}")
            print(f"   Ссылка: {hotel['link']}")
            print("-" * 50)

        # Сохранение в файл
        with open('hotels.txt', 'w', encoding='utf-8') as f:
            for hotel in hotels:
                f.write(f"Название: {hotel['title']}\n")
                f.write(f"Адрес: {hotel['address']}\n")
                f.write(f"Ссылка: {hotel['link']}\n\n")
        print(f"\nРезультаты сохранены в hotels.txt")

    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
    finally:
        driver.quit()