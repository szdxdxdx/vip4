#if !defined(__CS_IRES_ATTITUDE__)
#define __CS_IRES_ATTITUDE__

#include "../IP.h"

void CS_IRES_AttitudeFun(void *p);

typedef struct __IRESFILTER_PARAM
{
    float64    lmtDevAngle[2];      /* 红外地球敏感器组件的滚动安装偏差新息限幅阀值 */
    float64    Kg[3];               /* 根据陀螺指数漂移系数确定的滤波系数 */
    float64    KH1[6];              /* 姿态红外修正参数阵-滚动和偏航通道 */
    float64    KH2[3];              /* 姿态红外修正参数阵-俯仰通道 */

} IresFilterParam;


/* 模式切换指令处理 */
typedef struct __CS_IRES_Attitude
{
    /* 接口函数 */
    Fun     fun;

    /* 输入端口 */
    unint32 m_WorkMode;                             /* 当前模式 */
    float64 ModeObjectTimer_Mode[14];               /* 模式执行时间 */
    unint32 csAttPara_FS_AttD;                      /* 定姿方式标志 0 红外陀螺 1 星敏陀螺 2 星敏无陀螺(陀螺开) 3 星敏无陀螺(陀螺关) 4 红外无陀螺(陀螺关) */
    unint32 csModeData_CycleNum;                    /* 算法调用周期数 */
    unint32 csIresPara_FS[2];                       /* 红外i选取标志(0,不引入;1,引入) */
    unint32 csIresData_FHV[2];                      /* 红外i的硬件有效性标志(0:无效，1:有效) --- 接入 */
    float64 csIresData_S_Emz[2];                    /* 静态红外地球敏感器i的地心矢量z轴分量的符号 */
   
    /* 输出端口 */
    float64 csIresDiagData_Eb_i[2][3];              /* 由红外i测量计算的地心矢量在本体系的表示 */
    float64 csIresDiagData_Eb[3];
    float64 csIresDiagData_phi_i[2];                /* 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的滚动角  ES[i].φ */
    float64 csIresDiagData_theta_i[2];              /* 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的俯仰角 ES[i].θ */

    /* 输入输出端口 */
    unint32 csIresDiagData_FV[2];                   /* 红外有效性标志(0:无效，1:有效) */
    unint32 csIresDiagData_FU[2];                   /* 使用红外进行姿态修正标志(0:不使用，1:使用) */
    float64 csIresDiagData_Em[2][3];                /* 红外地球敏感器i测量的地心矢量在敏感器坐标系的表达 */

    float64 csIresData_phi;                         /* 由红外输出计算得到的滚动角 */
    float64 csIresData_theta;                       /* 由红外输出计算得到的俯仰角 */
    float64 csIresData_dPhi;                        /* 由红外测量计算的滚动角速度 */
    float64 csIresData_dTheta;                      /* 由红外测量计算的俯仰角速度 */

    float64 csAttCoreData_A_ESG[3];                 /* 星体三轴姿态(红外+陀螺) */
    float64 csGyroData_D0_ESCorr[3];                /* 地敏估陀螺本体系三轴常值漂移 rad/h */
    float64 csGyroData_De_ESCorr[3];                /* 地敏估陀螺本体系三轴指数漂移项 rad/h */
   
    /* 状态变量 */
    float64 csIresDiagData_phi_i_Lst[2];            /* 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的滚动角历史值 */
    float64 csIresDiagData_theta_i_Lst[2];          /* 系统误差补偿后的（或无补偿处理的）红外地球敏感器i测量处理的俯仰角历史值 */
    float64 csIresData_Cbs[2][3][3];                /* 红外1安装矩阵 由ES[i].CbsT转置得到 */
    unint32 csIresDiagData_CntEmx_ConstErr[2];      /* 静态红外弦宽常值计数器1 */
    unint32 csIresDiagData_CntEmy_ConstErr[2];      /* 静态红外基准常值计数器2 */
    float64 csIresData_phi_Lst;                     /* 由红外得到的前一次间接量测量 滚动角 */
    float64 csIresData_phi_Lst2;                    /* 由红外得到的前二次间接量测量 滚动角 */
    float64 csIresData_theta_Lst;                   /* 由红外得到的前一次间接量测量 俯仰角 */
    float64 csIresData_theta_Lst2;                  /* 由红外得到的前二次间接量测量 俯仰角 */
    float64 csIresDiagData_Em_Lst[2][3];            /* 红外地球敏感器i测量的地心矢量在敏感器坐标系的表达 */

    /* 参数变量 */
    float64 m_DeltaT;                               /* 控制周期 */
    float64 csModePara_dt_ESUsed_EIM;               /* 相对入轨段计时开始的红外引入时间（无红外时设置为大星时）*/
    unint32 csIresCorrPara_FP_IRESUse_AHM;          /* 偏置飞行模式下是否允许红外参与姿态修正以及系统故障检测 */
    unint32 csPointSunPara_gfhSPAttCalcMode;        /* FS_SCMType           对日姿态计算方法 0：轨道相位法 1：矢量叉乘法 2：连续偏航 */
    float64 csIresPara_Ts;                          /* 红外采样周期 */
    float64 csIresPara_CbsT[2][3][3];               /* 红外1安装矩阵 */

    float64 csIresPara_dphi_Comps;                  /* 红外滚动姿态偏差补偿量 */
    float64 csIresPara_dtheta_Comps;                /* 红外俯仰姿态偏差补偿量 */
    float64 csIresPara_dphib_Comps[2];              /* 红外地球敏感器i的系统误差（滚动轴） */
    float64 csIresPara_dthetab_Comps[2];            /* 红外地球敏感器i的系统误差（俯仰轴） */
    float64 csGyroPara_Mlf_D0;                      /* 陀螺常值漂移限幅值 */
    float64 csGyroPara_Mlf_De;                      /* 陀螺指数漂移限幅值 */    
    
    float64 csIresCorrPara_Mdf_f_dphi;              /* 红外差分角速度的滤波系数1（历史值系数）*/
    float64 csIresCorrPara_Mlf_dtheta;              /* 红外差分角速度限幅（俯仰轴） */
    float64 csIresCorrPara_Mlf_dphi;                /* 红外差分角速度限幅（滚动轴） */
    float64 csIresCorrPara_K_CorrDe_ESG[3];         /* 红外姿态修正的指数漂移修正系数 */
    float64 csIresCorrPara_K_Corrdphi_ESG[6];       /* 红外姿态修正滚动轴误差修正系数 */
    float64 csIresCorrPara_K_Corrdtheta_ESG[3];     /* 红外姿态修正俯仰轴误差修正系数 */

    unint32 csIresDiagPara_FP_ESProc[14];           /* 允许红外特殊处理的标志（轨道保护、常值判断、两红外一致性比对）*/
    unint32 csIresDiagPara_LmtN_ConstErr;           /* 连续次数限幅 */
	float64 csIresDiagPara_LmtEm_ConstErr;          /* Em常值检测阈值 */

} CS_IRES_Attitude;

#endif // __CS_IRES_ATTITUDE__
