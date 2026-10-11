/* std_mfexp.h - 规范化公共宏函数和宏表达式定义头文件 */
/* 2011.10.07, created */

#ifndef STD_TYPE_H
#define STD_TYPE_H

#include "std_basal.h"

/* CONVENIENT_FOR_LOOKUP
void type_convert(){} */
/* ----------------------------------------------------------------------------------------- */
/* 浮点转换为无符号整型数 */
/* ------------------------------------- */
/* 将32位单精度浮点数转换为32位无符号整型数 */
#define FLT_TO_UN32(x)    ((unint32)(x))

/* 将32位单精度浮点数转换为16位无符号整型数 */
#define FLT_TO_UN16(x)    ((unint16)(x))

/* 将32位单精度浮点数转换为8位无符号整型数 */
#define FLT_TO_UN08(x)    ((unint08)(x))

/* 将64位双精度浮点数转换为64位无符号整型数,会导致错误不能使用 */
#define DBL_TO_UN64(x)    ((ulong64)(x))

/* 将64位双精度浮点数转换为32位无符号整型数 */
#define DBL_TO_UN32(x)    ((unint32)(x))

/* 将64位双精度浮点数转换为16位无符号整型数 */
#define DBL_TO_UN16(x)    ((unint16)(x))

/* 将64位双精度浮点数转换为8位无符号整型数 */
#define DBL_TO_UN08(x)    ((unint08)(x))

/* 浮点转换为有符号整型数 */
/* ------------------------------------- */
/* 将32位单精度浮点数转换为32位有符号整型数 */
#define FLT_TO_SI32(x)    ((unint32)((siint32)(x)))

/* 将32位单精度浮点数转换为16位有符号整型数 */
#define FLT_TO_SI16(x)    ((unint16)((unint32)((siint32)(x))))

/* 将32位单精度浮点数转换为8位有符号整型数 */
#define FLT_TO_SI08(x)    ((unint08)((unint32)((siint32)(x))))

/* 将64位双精度浮点数转换为64位有符号整型数 */
#define DBL_TO_SI64(x)    ((ulong64)((llong64)(x)))

/* 将64位双精度浮点数转换为32位有符号整型数 */
#define DBL_TO_SI32(x)    ((unint32)((siint32)((float32)(x))))

/* 将64位双精度浮点数转换为16位有符号整型数 */
#define DBL_TO_SI16(x)    ((unint16)((siint32)((float32)(x))))

/* 无符号整型数转换为浮点 */
/* ------------------------------------- */
/* 将32位无符号整型数转换为32位单精度浮点数 */
#define UN32_TO_FLT(x)    ((float32)(x))

/* 将16位无符号整型数转换为32位单精度浮点数 */
#define UN16_TO_FLT(x)    ((float32)(x))

/* 将32位无符号整型数强制转换为双精度浮点数 */
#define UN32_TO_DBL(x)    ((float64)(x))

/* 将16位无符号整型数转换为64位双精度浮点数 */
#define UN16_TO_DBL(x)    ((float64)(x))

/* 将8位无符号整型数转换为64位双精度浮点数 */
#define UN08_TO_DBL(x)    ((float64)(x))

/* 有符号整型数转换为浮点 */
/* ------------------------------------- */
/* 将32位有符号整型数转换为32位单精度浮点数 */
#define SI32_TO_FLT(x)    ((float32)((siint32)(x)))

/* 将16位有符号整型数转换为32位单精度浮点数 */
#define SI16_TO_FLT(x)    ((float32)((siint16)(x)))

/* 将32位有符号整型数强制转换为双精度浮点数 */
#define SI32_TO_DBL(x)    ((float64)((siint32)(x)))

/* 将16位有符号整型数转换为64位双精度浮点数 */
#define SI16_TO_DBL(x)    ((float64)((siint16)(x)))

/* 将8位有符号整型数转换为64位双精度浮点数 */
#define SI08_TO_DBL(x)    ((float64)((siint08)(x)))

#endif /* STD_TYPE_H */
