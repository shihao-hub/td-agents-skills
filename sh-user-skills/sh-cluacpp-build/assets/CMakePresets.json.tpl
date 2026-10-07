{
  "version": 3,
  "cmakeMinimumRequired": { "major": 3, "minor": 21, "patch": 0 },
  "configurePresets": [
    {
      "name": "msvc-debug",
      "displayName": "MSVC x64 Debug (VS 生成器)",
      "generator": "Visual Studio 17 2022",
      "architecture": "x64",
      "binaryDir": "${sourceDir}/out/build/msvc-debug",
      "cacheVariables": {
        "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
      }
    },
    {
      "name": "clang-debug",
      "displayName": "Clang x64 Debug (Ninja)",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/out/build/clang-debug",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Debug",
        "CMAKE_C_COMPILER": "clang",
        "CMAKE_CXX_COMPILER": "clang++",
        "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
      }
    }
  ],
  "buildPresets": [
    {
      "name": "msvc-debug",
      "configurePreset": "msvc-debug",
      "configuration": "Debug"
    },
    {
      "name": "clang-debug",
      "configurePreset": "clang-debug"
    }
  ],
  "testPresets": [
    {
      "name": "msvc-debug",
      "configurePreset": "msvc-debug",
      "configuration": "Debug",
      "output": { "outputOnFailure": true }
    },
    {
      "name": "clang-debug",
      "configurePreset": "clang-debug",
      "output": { "outputOnFailure": true }
    }
  ]
}
