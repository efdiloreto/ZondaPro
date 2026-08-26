/*
 * Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>
 *
 * This file is part of Zonda.
 *
 * Zonda is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Zonda is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Zonda.  If not, see <https://www.gnu.org/licenses/>.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <shlwapi.h>

#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "shell32.lib")

static void obtener_directorio_base(wchar_t *buffer, DWORD max_len) {
    GetModuleFileNameW(NULL, buffer, max_len);
    PathRemoveFileSpecW(buffer);
}

static BOOL archivo_existe(const wchar_t *ruta) {
    DWORD attr = GetFileAttributesW(ruta);
    return (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY));
}

static BOOL directorio_existe(const wchar_t *ruta) {
    DWORD attr = GetFileAttributesW(ruta);
    return (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY));
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow) {
    (void)hInstance;
    (void)hPrevInstance;
    (void)nCmdShow;

    wchar_t base_dir[MAX_PATH];
    obtener_directorio_base(base_dir, MAX_PATH);

    // 1. Buscar el ejecutable de Python portable
    wchar_t python_exe[MAX_PATH];
    swprintf(python_exe, MAX_PATH, L"%s\\python\\pythonw.exe", base_dir);
    if (!archivo_existe(python_exe)) {
        swprintf(python_exe, MAX_PATH, L"%s\\python\\python.exe", base_dir);
    }
    if (!archivo_existe(python_exe)) {
        swprintf(python_exe, MAX_PATH, L"%s\\..\\python\\pythonw.exe", base_dir);
    }
    if (!archivo_existe(python_exe)) {
        swprintf(python_exe, MAX_PATH, L"%s\\..\\python\\python.exe", base_dir);
    }

    if (!archivo_existe(python_exe)) {
        MessageBoxW(
            NULL,
            L"No se pudo encontrar el entorno de ejecucion de Python en la carpeta 'python/'.\n"
            L"Verifique que la instalacion de Zonda este completa.",
            L"Zonda - Error al iniciar",
            MB_ICONERROR | MB_OK
        );
        return 1;
    }

    // 2. Inyectar tools/pandoc al PATH si existe
    wchar_t pandoc_dir[MAX_PATH];
    swprintf(pandoc_dir, MAX_PATH, L"%s\\tools\\pandoc", base_dir);
    if (directorio_existe(pandoc_dir)) {
        DWORD current_path_len = GetEnvironmentVariableW(L"PATH", NULL, 0);
        if (current_path_len > 0) {
            wchar_t *current_path = (wchar_t *)malloc(current_path_len * sizeof(wchar_t));
            if (current_path) {
                GetEnvironmentVariableW(L"PATH", current_path, current_path_len);
                size_t new_path_len = wcslen(pandoc_dir) + 1 + current_path_len + 1;
                wchar_t *new_path = (wchar_t *)malloc(new_path_len * sizeof(wchar_t));
                if (new_path) {
                    swprintf(new_path, new_path_len, L"%s;%s", pandoc_dir, current_path);
                    SetEnvironmentVariableW(L"PATH", new_path);
                    free(new_path);
                }
                free(current_path);
            }
        } else {
            SetEnvironmentVariableW(L"PATH", pandoc_dir);
        }
    }

    // 3. Configurar directorio de trabajo si existe la carpeta app/ o python/
    wchar_t app_dir[MAX_PATH];
    swprintf(app_dir, MAX_PATH, L"%s\\app", base_dir);
    if (!directorio_existe(app_dir)) {
        swprintf(app_dir, MAX_PATH, L"%s\\python", base_dir);
    }
    if (!directorio_existe(app_dir)) {
        swprintf(app_dir, MAX_PATH, L"%s", base_dir);
    }

    // 4. Armar la linea de comandos
    // Formato: "pythonw.exe" -m zonda.main [argumentos]
    size_t cmdline_len = wcslen(python_exe) + wcslen(pCmdLine) + 64;
    wchar_t *cmdline = (wchar_t *)malloc(cmdline_len * sizeof(wchar_t));
    if (!cmdline) {
        return 1;
    }

    if (wcslen(pCmdLine) > 0) {
        swprintf(cmdline, cmdline_len, L"\"%s\" -m zonda.main %s", python_exe, pCmdLine);
    } else {
        swprintf(cmdline, cmdline_len, L"\"%s\" -m zonda.main", python_exe);
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    BOOL success = CreateProcessW(
        python_exe,
        cmdline,
        NULL,
        NULL,
        FALSE,
        0,
        NULL,
        app_dir,
        &si,
        &pi
    );

    free(cmdline);

    if (!success) {
        DWORD err = GetLastError();
        wchar_t error_msg[512];
        swprintf(error_msg, 512, L"No se pudo iniciar el proceso de la aplicacion (Codigo de error %lu).", err);
        MessageBoxW(NULL, error_msg, L"Zonda - Error al iniciar", MB_ICONERROR | MB_OK);
        return 1;
    }

    // Esperar al proceso para propagar su codigo de salida
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exit_code = 0;
    GetExitCodeProcess(pi.hProcess, &exit_code);

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return (int)exit_code;
}

#else // macOS & Linux (POSIX)

#include <unistd.h>
#include <libgen.h>
#include <limits.h>
#include <sys/stat.h>

#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

static int archivo_existe_posix(const char *ruta) {
    struct stat st;
    return (stat(ruta, &st) == 0 && S_ISREG(st.st_mode));
}

static int directorio_existe_posix(const char *ruta) {
    struct stat st;
    return (stat(ruta, &st) == 0 && S_ISDIR(st.st_mode));
}

static void obtener_directorio_base_posix(char *buffer, size_t max_len) {
    char exe_path[PATH_MAX];
#ifdef __APPLE__
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) {
        strncpy(buffer, ".", max_len);
        return;
    }
#else
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len != -1) {
        exe_path[len] = '\0';
    } else {
        strncpy(buffer, ".", max_len);
        return;
    }
#endif
    char resolved[PATH_MAX];
    if (realpath(exe_path, resolved) != NULL) {
        char *dir = dirname(resolved);
        strncpy(buffer, dir, max_len);
    } else {
        char *dir = dirname(exe_path);
        strncpy(buffer, dir, max_len);
    }
}

int main(int argc, char *argv[]) {
    char base_dir[PATH_MAX];
    obtener_directorio_base_posix(base_dir, sizeof(base_dir));

    char python_exe[PATH_MAX];
    // 1. Buscar en estructura estándar de bundle o carpeta
    snprintf(python_exe, sizeof(python_exe), "%s/python/bin/python3", base_dir);
    if (!archivo_existe_posix(python_exe)) {
        // macOS bundle: Zonda.app/Contents/MacOS/zonda -> Zonda.app/Contents/Resources/python/bin/python3
        snprintf(python_exe, sizeof(python_exe), "%s/../Resources/python/bin/python3", base_dir);
    }
    if (!archivo_existe_posix(python_exe)) {
        // Entorno de desarrollo o relativo superior
        snprintf(python_exe, sizeof(python_exe), "%s/../python/.venv/bin/python", base_dir);
    }
    if (!archivo_existe_posix(python_exe)) {
        snprintf(python_exe, sizeof(python_exe), "%s/python/.venv/bin/python", base_dir);
    }
    if (!archivo_existe_posix(python_exe)) {
        // Fallback al python3 del sistema
        strncpy(python_exe, "python3", sizeof(python_exe));
    }

    // 2. Inyectar tools/pandoc al PATH si existe
    char pandoc_dir[PATH_MAX];
    snprintf(pandoc_dir, sizeof(pandoc_dir), "%s/tools/pandoc", base_dir);
    if (!directorio_existe_posix(pandoc_dir)) {
        snprintf(pandoc_dir, sizeof(pandoc_dir), "%s/../Resources/tools/pandoc", base_dir);
    }
    if (directorio_existe_posix(pandoc_dir)) {
        char *current_path = getenv("PATH");
        char new_path[PATH_MAX * 2];
        if (current_path) {
            snprintf(new_path, sizeof(new_path), "%s:%s", pandoc_dir, current_path);
        } else {
            snprintf(new_path, sizeof(new_path), "%s", pandoc_dir);
        }
        setenv("PATH", new_path, 1);
    }

    // 3. Inyectar PYTHONPATH para encontrar el paquete 'zonda'
    char app_dir[PATH_MAX];
    snprintf(app_dir, sizeof(app_dir), "%s/app", base_dir);
    if (!directorio_existe_posix(app_dir)) {
        snprintf(app_dir, sizeof(app_dir), "%s/../Resources/app", base_dir);
    }
    if (!directorio_existe_posix(app_dir)) {
        snprintf(app_dir, sizeof(app_dir), "%s/../python", base_dir);
    }
    if (!directorio_existe_posix(app_dir)) {
        snprintf(app_dir, sizeof(app_dir), "%s/python", base_dir);
    }
    if (directorio_existe_posix(app_dir)) {
        char *current_pypath = getenv("PYTHONPATH");
        char new_pypath[PATH_MAX * 2];
        if (current_pypath) {
            snprintf(new_pypath, sizeof(new_pypath), "%s:%s", app_dir, current_pypath);
        } else {
            snprintf(new_pypath, sizeof(new_pypath), "%s", app_dir);
        }
        setenv("PYTHONPATH", new_pypath, 1);
    }

    // 4. Armar argumentos para execv
    // argv nuevo: [python_exe, "-m", "zonda.main", argv[1], argv[2], ..., NULL]
    int new_argc = argc + 2;
    char **new_argv = (char **)malloc((new_argc + 1) * sizeof(char *));
    if (!new_argv) {
        perror("Error de asignacion de memoria en lanzador");
        return 1;
    }

    new_argv[0] = python_exe;
    new_argv[1] = "-m";
    new_argv[2] = "zonda.main";

    for (int i = 1; i < argc; i++) {
        new_argv[i + 2] = argv[i];
    }
    new_argv[new_argc] = NULL;

    execvp(python_exe, new_argv);

    // Si execvp retorna, hubo un error
    perror("Error al ejecutar Zonda");
    free(new_argv);
    return 1;
}

#endif
