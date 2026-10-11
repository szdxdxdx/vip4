#if !defined(__FG_333_SA_UNPACK_H__)
#define __FG_333_SA_UNPACK_H__

#include "IP.h"

/*
fg_3_3_3sa协议解析IP

功能描述：
  根据Fg333型光纤陀螺通信协议，解包由pRecvbuf指向的原始数据，
  并将其存储在SFg333saRaw结构体类型的指针pRaw所指向的内存中。

  1.解包陀螺头原始角速度  pRaw->wt0
  2.解包光路温度1       pRaw->glwd1
  3.解包光路温度2       pRaw->glwd2
  4.解包电路温度        pRaw->dlwd
  5.解包状态字          pRaw->status
  6.计算陀螺角度增量     pRaw->gf
*/

/* IP句柄函数类型 */
typedef void (*Fun)(void *);

typedef struct __Fg333saUnPack {
    /* 入口函数句柄 */
    Fun fun;

    /* 输入端口 */
    const unint08 *pRecvbuf; /* 陀螺原始数据缓冲区指针 */

    /* 输出端口 */
    float64 gf;     /* 角度增量 */
    float64 wt0;    /* 陀螺头原始角速度 */
    unint16 glwd1;  /* 光路温度1 */
    unint16 glwd2;  /* 光路温度2 */
    unint16 dlwd;   /* 电路温度 */
    unint08 status; /* 状态字 */

    /* 输入输出端口 */
    /* 无 */

    /* 状态变量 */
    /* 无 */

    /* 参数变量 */
    float64 dtime; /* 陀螺角度积分周期，量纲：s */

} Fg333saUnPack;

extern void Fg333saUnPackFun(void *pIp);
#define IPCALL(IP) (IP.fun(&IP))

#endif // __FG_333_SA_UNPACK_H__
