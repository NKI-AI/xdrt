#if   defined _WIN32
#define LIB_PRE __declspec(dllexport)
#else
#define LIB_PRE
#endif

#ifndef _nkidecompress_h_
#define _nkidecompress_h_
extern "C" {
	LIB_PRE int nki_private_decompress(short int *dest, signed char *src, int size);
}
#endif
