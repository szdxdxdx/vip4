/* std_common.h - 规范化公共要素头文件 */
/* 2015.06.16, created */

#ifndef STD_COMMON_H
#define STD_COMMON_H

#include "std_basal.h"

/* 定义基础公共运算使用的常量 */
#define  FLT32_ZERO  1.0e-7f                  /* 32位浮点0比较 */
#define  FLT64_ZERO  1.0e-14                  /* 64位浮点0比较 */
#define  HALF_PI     1.570796326794897        /* 半PI值 */
#define  PI          3.141592653589793        /* PI值 */
#define  DBL_PI      6.283185307179586        /* 2倍PI值 */
#define  DEG2RAD     0.0174532925199433       /* 度转弧度乘积系数 */
#define  RAD2DEG     57.29577951308232        /* 弧度转度乘积系数 */

#define  POW_2E_N6   1.5625e-2                /* pow(2, -6 ) */
#define  POW_2E_N10  9.765625e-4              /* pow(2, -10) */
#define  POW_2E_N11  4.8828125e-4             /* pow(2, -11) */
#define  POW_2E_N14  6.103515625e-5           /* pow(2, -14) */
#define  POW_2E_N15  3.0517578125e-5          /* pow(2, -15) */
#define  POW_2E_N22  2.384185791015625e-7     /* pow(2, -22) */
#define  POW_2E_N24  5.960464477539063e-8     /* pow(2, -24) */
#define  POW_2E_N30  9.313225746154785e-10    /* pow(2, -30) */

#endif /* STD_COMMON_H */
