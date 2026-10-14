#if !defined(__CS_TRGTATT_NWM_USU_H__)
#define __CS_TRGTATT_NWM_USU_H__

#include "../IP.h"

void CS_TrgtAtt_NWM_USUFun(void *p);

/* 模式切换指令处理 */
typedef struct __CS_TrgtAtt_NWM_USU
{
    /* 接口函数 */
    Fun     fun;

    /* 输入端口 */
    unint32 m_WorkMode;                             /* 当前模式 */
    float64 csDriftAngData_Psi_DA;                  /* 平滑后的实际偏流角 rad */
    unint32 csAttPara_Seq_AttD[14];                 /* 定姿转序（目前支持六种情况，132，123，231，213，312，321） */
    float64 csOrbData_w0i[3];                       /* 考虑轨道进动的轨道系相对于惯性系J2000.0的角速度 */
    float64 csDriftAngData_dPsi_DA;                 /* 平滑后的实际偏流角速度 rad/s */
    float64 csOrbData_coi[3][3];                    /* 从惯性系到轨道系的姿态转移矩阵 */

    /* 输出端口 */
    float64 csAttCoreData_wro[3];                   /* */
    float64 csMnvData_A_Ref_si[3];                  /* */
    float64 csAttCoreData_Cro[3][3];
    float64 csAttCoreData_Cro_si[3][3];			    /* CRO_Si */
    float64 csAttCoreData_wri[3];                   /* 三轴实时目标惯性角速度                                     */
    float64	csAttCoreData_wri_si[3];
    float64 csAttCoreData_qri[4];                   /* 参考系相对惯性系的目标姿态四元数                           */

    /* 输入输出端口 */

    /* 状态变量 */

    /* 参数变量 */
    float64 csAttCoreData_Cbiasp[3][3];             /* 姿态偏置矩阵 */
    float64 csLoadAxisData_Cbsi_DARot[3][3];        /* 视轴坐标系转换矩阵bsit */
    float64 csLoadAxisData_Csib_DARot[3][3];

} CS_TrgtAtt_NWM_USU;

#endif // __CS_TRGTATT_NWM_USU_H__