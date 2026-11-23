# Star Tracker — PC simulator and host tests. Builds the same portable source as the firmware:
#   firmware/common (link), firmware/rp2354a/motion (motion core), firmware/esp32s3/components/st_core + st_proto.
# Targets: startracker-sim (StarTrackerSim.exe on Windows) and st-tests (unit tests).
cmake_minimum_required(VERSION 3.16)
project(startracker_sim C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_STANDARD 11)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

include(FetchContent)
FetchContent_Declare(cjson GIT_REPOSITORY https://github.com/DaveGamble/cJSON.git GIT_TAG v1.7.18 GIT_SHALLOW TRUE)
FetchContent_GetProperties(cjson)
if(NOT cjson_POPULATED)
  FetchContent_Populate(cjson)
endif()
add_library(cjson STATIC ${cjson_SOURCE_DIR}/cJSON.c)
target_include_directories(cjson PUBLIC ${cjson_SOURCE_DIR})

set(FW ${CMAKE_CURRENT_LIST_DIR}/..)
add_library(stcore STATIC
  ${FW}/common/src/st_link.c
  ${FW}/rp2354a/motion/motion.c
  ${FW}/esp32s3/components/st_core/astro.cpp
  ${FW}/esp32s3/components/st_core/mount.cpp
  ${FW}/esp32s3/components/st_core/head.cpp
  ${FW}/esp32s3/components/st_proto/alpaca.cpp
  ${FW}/esp32s3/components/st_proto/lx200.cpp
  ${FW}/esp32s3/components/st_proto/wsapi.cpp
  ${FW}/esp32s3/components/st_proto/services.cpp
  src/sim_head.cpp)
target_include_directories(stcore PUBLIC ${FW}/common/include ${FW}/rp2354a/motion
  ${FW}/esp32s3/components/st_core/include ${FW}/esp32s3/components/st_proto/include src)
target_link_libraries(stcore PUBLIC cjson)
if(NOT MSVC)
  target_compile_options(stcore PRIVATE -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers)
endif()

find_package(Threads REQUIRED)
add_executable(startracker-sim src/sim_main.cpp src/net.cpp)
target_link_libraries(startracker-sim stcore Threads::Threads)
if(WIN32)
  target_link_libraries(startracker-sim ws2_32)
  set_target_properties(startracker-sim PROPERTIES OUTPUT_NAME StarTrackerSim)
endif()
target_compile_definitions(startracker-sim PRIVATE WEB_INDEX="${FW}/common/web/index.html")

file(GLOB TESTS ${FW}/tests/unit/test_*.cpp)
add_executable(st-tests ${FW}/tests/unit/main.cpp ${TESTS})
target_link_libraries(st-tests stcore Threads::Threads)
target_include_directories(st-tests PRIVATE ${FW}/tests/unit)
enable_testing()
add_test(NAME unit COMMAND st-tests)
