import numpy as np
import pytest
from utils.Model import Model
from openpyxl import Workbook

# Определяем диапазоны значений параметров для тестирования
Dx_values = [0.1, 0.5, 1.0, 2.0, 5.0]
Dy_values = [0.1, 0.5, 1.0, 2.0, 5.0]
v_values = [0, 5, 10, 15, 20]
u_values = [0, 5, 10, 15, 20]

# Создаем Excel книгу и лист
wb = Workbook()
ws = wb.active
ws.title = "Stability Results"

# Заголовки столбцов
headers = ["Dx", "Dy", "u", "v", "Stability", "CFL"]
ws.append(headers)

# Фикстура для сохранения файла после всех тестов
@pytest.fixture(scope="session", autouse=True)
def save_excel_file():
    yield
    wb.save("C:/Users/user/Desktop/stability_results.xlsx")
    print("Файл сохранен")

@pytest.mark.parametrize("Dx, Dy, u, v",
                         [(Dx, Dy, u, v) for Dx in Dx_values for Dy in Dy_values for u in u_values for v in v_values])
def test_stability(Dx, Dy, u, v):
    """Тест на устойчивость решения при заданных параметрах."""
    try:
        condit_start = np.zeros((50, 50))
        condit_start[25][25] = 1

        model = Model(
            c_start=condit_start,
            Dx=Dx,
            Dy=Dy,
            u=u,
            v=v,
            check_stable=True,
            check_cfl=False
        )
        CFL = 0.1 * u / 1 + 0.1 * v / 1 + 2 * Dx * 0.1 / 1 ** 2 + 2 * Dy * 0.1 / 1 ** 2
        model.iterate()
        is_stable = True
        stability = "Устойчиво"
    except Exception as e:
        if "Решение расходится" in str(e):
            is_stable = False
            stability = "Неустойчиво"
        else:
            raise

    # Записываем данные в Excel
    ws.append([Dx, Dy, u, v, stability, CFL])

    # Для наглядности выводим результат теста
    print(f"Dx={Dx}, Dy={Dy}, u={u}, v={v} - {stability}")