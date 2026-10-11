#if !defined(__CALCULATEGYRORS_H__)
#define __CALCULATEGYRORS_H__

#include "IP.h"

void CalculateGyroRsFun(void *p);

/* 计算陀螺相关矩阵 */
typedef struct __CalculateGyroRs {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    unint08 JoinTotal;   /* 参加定姿的陀螺个数 */
    unint16 gyroStatus0; /* 陀螺状态旧 */
    unint08 *SignFlag;   /* 参加定姿的陀螺序号数组指针 */

    /* 输出端口 */
    unint08 flgGryoCalc; /* 陀螺计算标志 */
    float32 Rtemp[3][5]; /* 矩阵计算结果 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    unint16 gyroStatus1; /* 陀螺状态新 */

    /* 参数变量 */
    float32 VG[9][3];
} CalculateGyroRs;

#endif // __CALCULATEGYRORS_H__
