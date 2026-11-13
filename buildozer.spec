[app]

title = Mergulho Bühlmann
package.name = divecalc
package.domain = org.mergulho

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = tests,bin,.buildozer,__pycache__

version = 1.0

# Dependências — matplotlib precisa de numpy e pillow
requirements = python3,kivy==2.3.0,kivymd==1.2.0,matplotlib,numpy,pillow

orientation = portrait
fullscreen = 0

# Android
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 33.0.2
android.archs = arm64-v8a
android.allow_backup = True
android.permissions =
android.copy_libs = 1

# iOS (não usado aqui, mas reservado)
# ios.kivy_ios_url = https://github.com/kivy/kivy-ios

[buildozer]
log_level = 2
warn_on_root = 1
