import os

EXCLUDE_DIRS = {
    'node_modules',
    '.git', 
    '__pycache__', 
    'venv', 
    '.venv', 
    'dist', 
    'build', 
    'icons', 
    'assets', 
    'img',
    '.pytest_cache',
    'htmlcov',
    '.coverage'
}

EXCLUDE_FILES = {
    'package-lock.json', 
    '.gitignore', 
    'full.txt', 
    'collect_files.py', 
    'collect.py', 
    'package.json', 
    'README.md', 
    'Readme.md', 
    'readme.md'
}


def is_text_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(1024)
        return True
    except (UnicodeDecodeError, OSError):
        return False

def collect_all_files(output_file="full.txt"):
    current_dir = "."
    abs_output_path = os.path.abspath(output_file)

    with open(output_file, "w", encoding="utf-8") as out_f:
        for dirpath, dirnames, filenames in os.walk(current_dir):
            # Удаляем исключённые директории из обхода
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

            for filename in filenames:
                if filename in EXCLUDE_FILES:
                    continue

                file_abs = os.path.join(dirpath, filename)
                # Пропускаем, если output_file сам попал в обход
                if os.path.abspath(file_abs) == abs_output_path:
                    continue

                rel_path = os.path.relpath(file_abs, current_dir).replace(os.sep, '/')
                
                # Дополнительная проверка на случай, если путь всё же содержит исключённую директорию
                if any(excl_dir in rel_path.split('/') for excl_dir in EXCLUDE_DIRS):
                    continue

                out_f.write(f"{rel_path}\n")
                if is_text_file(file_abs):
                    try:
                        with open(file_abs, "r", encoding="utf-8") as f:
                            content = f.read()
                        out_f.write(content)
                    except Exception as e:
                        out_f.write(f"[Ошибка при чтении файла: {e}]\n")
                else:
                    out_f.write("[Binary or non-text file]\n")
                out_f.write("\n\n")

if __name__ == "__main__":
    collect_all_files()
    print("Сбор содержимого всех файлов завершён. Результат — в full.txt")