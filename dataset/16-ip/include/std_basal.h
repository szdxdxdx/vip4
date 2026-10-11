/* std_basal.h - 规范化基本数据类型定义头文件 */
/* 2013.11.29 */
#ifndef STD_BASAL_H
#define STD_BASAL_H

/* 快仿定义 */
#define FAST_SIMULATOR      1

typedef signed   char   siint08;
typedef unsigned char   unint08;
typedef short           siint16;
typedef unsigned short  unint16;
typedef int             siint32;
typedef unsigned int    unint32;
typedef float           float32;
typedef double          float64;

typedef unsigned int    boolu32;    /* 二态布尔型 */
typedef unsigned int    dimorph;    /* 二态型 */
typedef unsigned int    polymor;    /* 多态的 */

#ifdef __GCC_COMPILED__
typedef long long           llong64;
typedef unsigned long long  ulong64;
#else
typedef __int64           llong64;
typedef unsigned __int64  ulong64;
#endif


#define TRUE32   0xEB90146F  /* 逻辑真 */
#define FALSE32  0x00000000  /* 逻辑假 */

/* ----------------------------------------------------------------------------------------- */
/* 空语句占位代码 */
#define NULL_STATEMENT()    {_nullStatement = 0;}


#ifdef __GCC_COMPILED__
  /* SPARC-RTMES-GCC Compiler Only */
  #define PACKED                    __attribute__ ((aligned(1), packed))
#else
  #define PACKED
#endif

#endif  /* STD_BASAL_H */
