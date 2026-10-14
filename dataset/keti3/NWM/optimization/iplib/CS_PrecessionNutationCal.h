#if !defined(__CS_PRECESSIONNUTATIONCAL_H__)
#define __CS_PRECESSIONNUTATIONCAL_H__

#include "../../IP.h"

// 函数声明
void CS_PrecessionNutationCalFun(void *p);

// IP 结构体定义
typedef struct __CS_PrecessionNutationCal
{
    /* 函数接口 */
    // Fun     fun;

    /* 输入变量 */
    float64 tmpT;
//    unint32 csOrbOtherPara_FS_CPNCal;       /* 岁差章动矩阵在轨计算标志 */

    /* 输出变量 */
//    unint32 csOrbDataOther_F_qJDerr;        /*  */
//	float64 CPN[3][3];						/* 岁差章动矩阵 */

    /* 输入输出变量 */
//    float64 csOrb19_qd[4];                  /* 岁差章动四元数，qJD[0]～qJD[2]为矢量部分，qJD[3]为标量部分 */

    /* 状态变量*/

    /* 参数变量 */
//    float64 csOrb19_Para_I_UTC0;            /* 星时计时零点相对 GPS 计时零点的时间间隔 */
//    float64 csGpsPara_dT_UTC2TDT;           /* GPS计时零点UTC与TDT的时间差（=跳秒+32.184） */
//    float64 csGpsPara_tGPS0;                /* GPS计时零点相对于J2000.0的时间间隔 */

} CS_PrecessionNutationCal;

#endif // __CS_PRECESSIONNUTATIONCAL_H__