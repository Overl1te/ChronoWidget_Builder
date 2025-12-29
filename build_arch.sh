#!/bin/bash
# build_arch.sh - Скрипт сборки ChronoDash Builder

set -e

# === КОНФИГУРАЦИЯ ===
APP_NAME="ChronoBuilder"       # Имя для пользователя
BINARY_NAME="ChronoBuilder"    # Имя исполняемого файла
INSTALL_DIR="/opt/chronobuilder"
MAIN_SCRIPT="main.py"
ICON_SRC="assets/icons/chronodash.png" # Путь к иконке в исходниках

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Сборка $APP_NAME для Arch Linux ===${NC}"

# 1. ОЧИСТКА
echo -e "${GREEN}[1/5] Очистка предыдущих сборок...${NC}"
rm -rf build/ dist/ *.spec __pycache__/ *.pyc venv/

# 2. ПОДГОТОВКА ОКРУЖЕНИЯ
echo -e "${GREEN}[2/5] Создание виртуального окружения...${NC}"
python3 -m venv venv
source venv/bin/activate

echo "Установка зависимостей..."
pip install --upgrade pip
pip install pyinstaller

# Проверка requirements.txt, иначе ставим минимальный набор для билдера
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt не найден, устанавливаю PySide6..."
    pip install PySide6
fi

# 3. СБОРКА ЧЕРЕЗ PYINSTALLER
echo -e "${GREEN}[3/5] Запуск PyInstaller...${NC}"

# Формируем аргументы для ресурсов (если папка assets существует)
ADD_DATA_ARGS=""
if [ -d "assets" ]; then
    ADD_DATA_ARGS="--add-data assets:assets"
    echo "Найдена папка assets, включаем в сборку."
fi

# Сборка
pyinstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name "$BINARY_NAME" \
    --clean \
    $ADD_DATA_ARGS \
    --hidden-import PySide6.QtNetwork \
    --hidden-import PySide6.QtSvg \
    --hidden-import PySide6.QtPrintSupport \
    --exclude-module tkinter \
    --exclude-module matplotlib \
    --exclude-module scipy \
    --exclude-module numpy \
    --exclude-module pandas \
    --exclude-module pystray \
    --exclude-module PIL \
    "$MAIN_SCRIPT"

echo -e "${GREEN}[4/5] Генерация скриптов запуска и установки...${NC}"

# Переходим в папку сборки
cd "dist/$BINARY_NAME"

# --- СОЗДАНИЕ LAUNCH.SH (Запуск) ---
cat > launch.sh << EOF
#!/bin/bash
# Скрипт запуска $APP_NAME

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR"

# Определение путей (совместимость с PyInstaller > 6.0)
if [ -f "./$BINARY_NAME" ]; then
    EXEC="./$BINARY_NAME"
    INTERNAL="./_internal"
elif [ -f "./_internal/$BINARY_NAME" ]; then
    EXEC="./_internal/$BINARY_NAME"
    INTERNAL="./_internal"
else
    # Fallback поиск
    EXEC=\$(find . -type f -name "$BINARY_NAME" -executable -print -quit)
    INTERNAL="\$(dirname "\$EXEC")"
fi

if [ -z "\$EXEC" ]; then
    echo "Ошибка: Исполняемый файл не найден!"
    exit 1
fi

chmod +x "\$EXEC"

# Фикс для Wayland/X11 и Qt плагинов
export QT_PLUGIN_PATH="\$INTERNAL/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="\$INTERNAL/PySide6/Qt/plugins"

# Запуск
exec "\$EXEC" "\$@"
EOF
chmod +x launch.sh

# --- СОЗДАНИЕ INSTALL.SH (Установка) ---
cat > install.sh << EOF
#!/bin/bash
# Скрипт установки $APP_NAME в систему

set -e

if [ "\$EUID" -eq 0 ]; then
    echo "Ошибка: Запустите через sudo ./install.sh"
    exit 1
fi

echo "=== Установка $APP_NAME ==="

# 1. Установка системных либ (для Qt)
echo "Проверка зависимостей..."
if command -v pacman &> /dev/null; then
    sudo pacman -S --noconfirm --needed qt6-base qt6-svg
fi

# 2. Копирование файлов
echo "Копирование файлов в $INSTALL_DIR..."
sudo rm -rf $INSTALL_DIR
sudo mkdir -p $INSTALL_DIR
sudo cp -r ./* $INSTALL_DIR/

# 3. Настройка прав
echo "Настройка прав доступа..."
sudo chown -R root:root $INSTALL_DIR
sudo find $INSTALL_DIR -type d -exec chmod 755 {} \;
sudo find $INSTALL_DIR -type f -exec chmod 644 {} \;
sudo chmod +x $INSTALL_DIR/launch.sh
sudo find $INSTALL_DIR -name "$BINARY_NAME" -exec chmod 755 {} \;

# 4. Создание бинарника в PATH
echo "Создание ссылки /usr/bin/chronobuilder..."
sudo tee /usr/bin/chronobuilder > /dev/null << 'BIN'
#!/bin/bash
exec "$INSTALL_DIR/launch.sh" "\$@"
BIN
sudo chmod +x /usr/bin/chronobuilder

# 5. Иконка
echo "Настройка иконки..."
ICON_DEST="/usr/share/icons/hicolor/256x256/apps"
sudo mkdir -p "\$ICON_DEST"

# Пытаемся найти иконку внутри сборки
if [ -f "$INSTALL_DIR/$ICON_SRC" ]; then
    sudo cp "$INSTALL_DIR/$ICON_SRC" "\$ICON_DEST/chronobuilder.png"
elif [ -f "$INSTALL_DIR/_internal/$ICON_SRC" ]; then
    sudo cp "$INSTALL_DIR/_internal/$ICON_SRC" "\$ICON_DEST/chronobuilder.png"
else
    # Заглушка, если иконки нет
    sudo touch "\$ICON_DEST/chronobuilder.png"
fi

# 6. Desktop файл
echo "Создание ярлыка меню..."
sudo mkdir -p /usr/share/applications
sudo tee /usr/share/applications/chronobuilder.desktop > /dev/null << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=$APP_NAME
GenericName=Widget Builder
Comment=Create and edit widgets for ChronoDash
Exec=/usr/bin/chronobuilder
Icon=chronobuilder
Terminal=false
Categories=Development;Utility;Qt;Design;
StartupNotify=true
DESKTOP

echo "✅ Установка завершена!"
echo "Запустите команду: chronobuilder"
EOF
chmod +x install.sh

# --- СОЗДАНИЕ UNINSTALL.SH (Удаление) ---
cat > uninstall.sh << EOF
#!/bin/bash
# Удаление $APP_NAME

if [ "\$EUID" -eq 0 ]; then
    echo "Запустите через sudo ./uninstall.sh"
    exit 1
fi

echo "Удаление $APP_NAME..."
sudo rm -rf $INSTALL_DIR
sudo rm -f /usr/bin/chronobuilder
sudo rm -f /usr/share/applications/chronobuilder.desktop
sudo rm -f /usr/share/icons/hicolor/256x256/apps/chronobuilder.png

echo "✅ Удалено."
EOF
chmod +x uninstall.sh

echo -e "${GREEN}[5/5] Сборка завершена успешно!${NC}"
echo "------------------------------------------------"
echo -e "Результат находится в: ${BLUE}dist/$BINARY_NAME/${NC}"
echo -e "1. Для проверки запустите: ${BLUE}./dist/$BINARY_NAME/launch.sh${NC}"
echo -e "2. Для установки запустите: ${BLUE}cd dist/$BINARY_NAME && sudo ./install.sh${NC}"