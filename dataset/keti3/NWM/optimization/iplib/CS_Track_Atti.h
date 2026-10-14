#if !defined(__CS_TRACK_ATTI_H__)
#define __CS_TRACK_ATTI_H__

#include "../../IP.h"

void CS_Track_AttiFun(void *p);

/* 模式切换指令处理 */
typedef struct __CS_Track_Atti
{
    /* 接口函数 */
    // Fun     fun;

    /* 输入端口 */
//    unint32 m_WorkMode;                         /* 当前模式 */
//    float64 csAttCoreData_Cro[3][3];
//    unint32 csAttPara_Seq_AttD[14];             /* 定姿转序（目前支持六种情况，132，123，231，213，312，321） */
//    float64 csAttCoreData_wro[3];               /* */
//    float64 csAttCoreData_wri[3];               /* 三轴实时目标惯性角速度                                     */

    /* 输出端口 */
//    float64 csMnvData_A_Ref[3];                 /* 三轴实时目标姿态 */
//    float64 csMnvData_dA_Ref[3];                /* 三轴实时目标姿态角速度 */
//    float64 csMnvData_ddA_Ref[3];               /* 三轴实时目标姿态角加速度 */
//    float64 csMnvData_TorqRef[3];               /* 前馈力矩补偿 */

    /* 输入输出端口 */

    /* 状态变量 */
    float64 csMnvData_dA_Ref_Lst[3];            /* */
    float64 csAttCoreData_wri_Lst[3];           /* */

    /* 参数变量 */
//    float64 m_DeltaT;                           /* 控制周期 */
//    float64 csCtrlerData_Js_Use[3][3];          /* 当前选用的星体惯量矩阵 */
//    float64 csCtrlerOtherPara_Mdf_TorqRef;      /* 姿态机动前馈力矩的修正系数 */
//    float64 csCtrlerOtherPara_Mlf_TorqRef;      /* 前馈力矩模的限幅，超过则力矩清零 */

} CS_Track_Atti;

#endif // __CS_TRACK_ATTI_H__