#ifndef STD_UTILS_H
#define STD_UTILS_H

#include <math.h>
#include "std_basal.h"
#include "std_common.h"

/* 不同使用场景编译命令 */
#ifdef __GCC_COMPILED__     /* 编译GCC静态库 */
    #define  DECLARE   extern
#elif  __VC_COMPILED__      /* 编译VC静态库 */
    #define  DECLARE   extern  "C" __declspec(dllexport)
#else                       /* 调用VC静态库 */
    #define  DECLARE   extern  "C" __declspec(dllimport)
#endif
   unint32 _nullStatement;

   unint08 CheckSumAdd08(const unint08 *buffer, unint32 length);

#endif
