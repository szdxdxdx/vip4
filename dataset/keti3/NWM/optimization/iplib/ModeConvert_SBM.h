#if !defined(__MODECONVERT_SBM_H__)
#define __MODECONVERT_SBM_H__

#include "../../IP.h"

void ModeConvert_SBMFun(void *p);

/* 模式切换指令处理 */
typedef struct __ModeConvert_SBM
{
    /* 接口函数*/
    // Fun     fun;

    /* 输入端口*/
//    float64 m_starTime;                          /* 当前星时 t */

    /* 输出端口 */
//    unint32 m_WorkMode;                          /* 当前模式 */

    /* 输入输出端口 */

    /* 状态变量 */

    /* 参数变量 */
//    float64 csOrb19_Para_I_t0;                   /* 使用的轨道参数的参考时刻 */
//    float64 csModePara_dt_OrbitInject;           /* 星箭分离到入轨段计时开始的相对时间 */

} ModeConvert_SBM;

#endif // __MODECONVERT_SBM_H__