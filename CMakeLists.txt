CMAKE_MINIMUM_REQUIRED(VERSION 3.6)
PROJECT(NKIDECOMPRESS)

SET(SOURCE_DIR "xdrt/lib/nki_decompression")

INCLUDE_DIRECTORIES(${SOURCE_DIR})


SET(NKIDECOMPRESS_SRC
    ${SOURCE_DIR}/nkidecompress.cxx
    )

ADD_LIBRARY(nkidecompress SHARED "${NKIDECOMPRESS_SRC}")
TARGET_LINK_LIBRARIES(nkidecompress)
