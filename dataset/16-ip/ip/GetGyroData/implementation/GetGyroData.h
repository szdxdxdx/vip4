#if !defined(__GETGYRODATA_H__)
#define __GETGYRODATA_H__

#include "IP.h"

void GetGyroDataFun(void *p);

#define DIVIATION_TO_FLOAT_DSS(x) \
    DiviationToFloat((x), 0xFFF, 0x800, 2.44140625e-3f) /*  5/2048 -5~5° */
#define DIVIATION_TO_FLOAT_GYRO(x) \
    DiviationToFloat((x), 0xFFF, 0x800, 1.62760417e-3f) /*  5/3072 -2.5~2.5°/S */
#define DIVIATION_TO_FLOAT_FOG(x) \
    DiviationToFloat((x), 0xFFF, 0x800, 9.765625e-4f) /* 1/1024° */

#define TYPE_GYRO 0
#define TYPE_FOG 1

/* 陀螺数据采集 */
typedef struct __GetGyroData {
    /* 接口函数 */
    Fun fun;

    /* 输入端口 */
    /* 无 */

    /* 输出端口 */
    float32 wa[9]; /* 陀螺角速度模拟量 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    /* 无 */

    /* 参数变量 */
    unint16 ADDR_AD_START; /* AD采集启动地址 0xA000 */
    unint16 AD_GYRO_LO4;   /* AD采集数据低4位地址 0xA003 */
    unint16 AD_GYRO_HI8;   /* AD采集数据高8位地址 0xA001 */
    unint08 chnl[9];       /* 9个陀螺AD采集通道号 */
    unint08 type[9];       /* 9个陀螺类型 */
} GetGyroData;

#endif // __GETGYRODATA_H__
