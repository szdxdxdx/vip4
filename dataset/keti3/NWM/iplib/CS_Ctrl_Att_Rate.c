#include "CS_Ctrl_Att_Rate.h"

void CS_Angle2CX_temp2(void *p);

void CS_Ctrl_Att_RateFun(void *p) 
{
    CS_Ctrl_Att_Rate *pIp = (CS_Ctrl_Att_Rate*)p;
    float64 wbt[3];
    float64 tmp[3][3];
    unint32 i,j;
    unint32 WorkMode = pIp->m_WorkMode;

    /* (1) 全捕姿态控制量赋值 */
    if (pIp->csCtrlerOtherPara_FS_ModeProc[WorkMode] == 2)
    {
        for (i=0; i<3; i++)
        {
            pIp->csAttCoreData_A_Clp[i]    = pIp->csSGAttAcqData_A[i];   /* 遥测使用  */
            pIp->csAttCoreData_Rate_Clp[i] = pIp->csSGAttAcqData_dA[i];  /* 角速度控制量偏差 */
            pIp->csAttCoreData_wbo_Clp[i]  = pIp->csSGAttAcqData_w[i];   /* 实际星体搜索角速度 */

            pIp->csAttCoreData_A_c[i]    = pIp->csSGAttAcqData_A[i];
            pIp->csAttCoreData_Rate_c[i] = pIp->csSGAttAcqData_dA[i];
        }
    }
    else
    {
    #if 1 //_INCLUDE_ANT_
        /* (2) 历史值赋值 用于机动过程中天线转角外推 */
        if ((pIp->csAntPara_LmtH_Num_dw > 0) && (pIp->csAntPara_LmtH_Num_dw <= 20))  /* 防越界保护  MAX_LMTH_NUM_DW 20*/
        {
            for (i=(pIp->csAntPara_LmtH_Num_dw-1); i>0; i--)
            {
                pIp->csAttCoreData_wbo_Lst[i][0] = pIp->csAttCoreData_wbo_Lst[i-1][0];
                pIp->csAttCoreData_wbo_Lst[i][1] = pIp->csAttCoreData_wbo_Lst[i-1][1];
                pIp->csAttCoreData_wbo_Lst[i][2] = pIp->csAttCoreData_wbo_Lst[i-1][2];
            }
            pIp->csAttCoreData_wbo_Lst[0][0] = pIp->csAttCoreData_wbo_Clp[0];
            pIp->csAttCoreData_wbo_Lst[0][1] = pIp->csAttCoreData_wbo_Clp[1];
            pIp->csAttCoreData_wbo_Lst[0][2] = pIp->csAttCoreData_wbo_Clp[2];
        }
    #endif
        /* (3) 陀螺关闭情况下的姿态赋值 */
        if (pIp->csAttPara_FS_AttD == 3)             /* 星敏无陀螺定姿，陀螺关 */
        {
            for (i=0; i<4; i++)
            {
                pIp->csAttCoreData_q_STG[i] = pIp->csAttCoreData_q_STDyn[i];
            }

            for (i=0; i<3; i++)
            {
                pIp->csAttCoreData_w_STG[i] = pIp->csAttCoreData_w_STDyn[i];
            }

            pIp->csAttCoreData_A_ESG[0] = pIp->csIresData_phi;
            pIp->csAttCoreData_A_ESG[1] = pIp->csIresData_theta;
            pIp->csAttCoreData_A_ESG[2] = pIp->csMnvData_A_Ref[2];
        }

        if (pIp->csAttPara_FS_AttD == 4)             /* 红外无陀螺定姿，红外关 */
        {
            pIp->csAttCoreData_A_ESG[0] = pIp->csIresData_phi;
            pIp->csAttCoreData_A_ESG[1] = pIp->csIresData_theta;
            pIp->csAttCoreData_A_ESG[2] = 0.0;

            CS_Angle2CX_temp2(pIp);
        }

        /* (4) 姿态及角速度赋值 */
        /* 红外 + 陀螺 */
        if (pIp->csAttPara_FS_AttD == 0)
        {
            for (i=0; i<3; i++)
            {
                pIp->csAttCoreData_A_Clp[i]  = pIp->csAttCoreData_A_ESG[i];
                pIp->csAttCoreData_Rate_Clp[i]  = pIp->csAttCoreData_Rate_ESG[i];
                pIp->csAttCoreData_wbo_Clp[i] = pIp->csAttCoreData_wbo_ESG[i];
                pIp->csAttCoreData_w_Clp[i] = pIp->csAttCoreData_w_ESG[i];

                for (j=0; j<3; j++)
                {
                    pIp->csAttCoreData_Cbo_Clp[i][j] = pIp->csAttCoreData_Cbo_ESG[i][j];
                }
            }
        }

        /* 星敏 + 陀螺定姿 */
        else if (pIp->csAttPara_FS_AttD == 1)
        {
            for (i=0; i<3; i++)
            {
                pIp->csAttCoreData_Rate_Clp[i]  = pIp->csAttCoreData_Rate_STG[i];
                pIp->csAttCoreData_A_Clp[i]  = pIp->csAttCoreData_A_STG[i];
                pIp->csAttCoreData_wbo_Clp[i] = pIp->csAttCoreData_wbo_STG[i];
                pIp->csAttCoreData_w_Clp[i] = pIp->csAttCoreData_w_STG[i];

                for (j=0; j<3; j++)
                {
                    pIp->csAttCoreData_Cbo_Clp[i][j] = pIp->csAttCoreData_Cbo_STG[i][j];
                }
            }
        }

        /* 星敏无陀螺定姿 */
        else if ((pIp->csAttPara_FS_AttD == 2) || (pIp->csAttPara_FS_AttD == 3))
        {
            for (i=0; i<3; i++)
            {
                pIp->csAttCoreData_A_Clp[i]  = pIp->csAttCoreData_A_STDyn[i];
                pIp->csAttCoreData_Rate_Clp[i]  = pIp->csAttCoreData_Rate_STDyn[i];
                pIp->csAttCoreData_wbo_Clp[i] = pIp->csAttCoreData_wbo_STDyn[i];
                pIp->csAttCoreData_w_Clp[i] = pIp->csAttCoreData_w_STDyn[i];

                for (j=0; j<3; j++)
                {
                    pIp->csAttCoreData_Cbo_Clp[i][j] = pIp->csAttCoreData_Cbo_STDyn[i][j];
                }
            }
        }
        /* 红外无陀螺定姿 */
        else if (pIp->csAttPara_FS_AttD == 4)
        {
            for (i=0; i<3; i++)
            {
                pIp->csAttCoreData_wbo_Clp[i] = 0.0;
                for (j=0; j<3; j++)
                {
                    pIp->csAttCoreData_Cbo_Clp[i][j] = pIp->csAttCoreData_Cbo_ESG[i][j];
                }
            }

            MatrixMulti331(pIp->csAttCoreData_w_Clp, pIp->csAttCoreData_Cbo_ESG[0], pIp->csOrbData_w0i);

            pIp->csAttCoreData_A_Clp[0] = pIp->csIresData_phi;
            pIp->csAttCoreData_A_Clp[1] = pIp->csIresData_theta;
            pIp->csAttCoreData_A_Clp[2] = 0.0;

            pIp->csAttCoreData_Rate_Clp[0] = pIp->csIresData_dPhi;
            pIp->csAttCoreData_Rate_Clp[1] = pIp->csIresData_dTheta;
            pIp->csAttCoreData_Rate_Clp[2] = 0.0;
        }
        else
        {
            /* 空分支 */
            OP_NOP;
        }

        /* (5) 姿态及角速度偏差计算 */
        /* 姿态偏差历史值 */
        for (i=0; i<3; i++)
        {
            pIp->csAttCoreData_A_c_Lst[i] = pIp->csAttCoreData_A_c[i];
        }

        pIp->csAttCoreData_angqbt_Lst = Acosx(pIp->csAttCoreData_qbt[3]);

        if (pIp->csCtrlerOtherPara_FP_BMC == 1)      /* 偏置动量 */
        {
            for (i=0; i<3; i++)
            {
                pIp->csAttCoreData_A_c[i] = pIp->csAttCoreData_A_Clp[i];
                pIp->csAttCoreData_Rate_c[i] = pIp->csAttCoreData_Rate_Clp[i];

                if (i == 2)
                {
                    pIp->csAttCoreData_A_c[i] = 0.0;
                    pIp->csAttCoreData_Rate_c[i] = 0.0;
                }
            }
        }
        else        /* 零动量 */
        {
            if (pIp->csAttPara_FS_AttD == 1)
            {
                Qdiv(pIp->csAttCoreData_qbt, pIp->csAttCoreData_qri, pIp->csAttCoreData_q_STG);

                for (i=0; i<3; i++)
                {
                    wbt[i] = pIp->csAttCoreData_w_STG[i] - pIp->csAttCoreData_wri[i];
                }
            }
            else if ((pIp->csAttPara_FS_AttD == 2) || (pIp->csAttPara_FS_AttD == 3))
            {
                Qdiv(pIp->csAttCoreData_qbt, pIp->csAttCoreData_qri, pIp->csAttCoreData_q_STDyn);

                for (i=0; i<3; i++)
                {
                    wbt[i] = pIp->csAttCoreData_w_STDyn[i] - pIp->csAttCoreData_wri[i];
                }
            }
            else    /* csAttPara_FS_AttD == 0 */
            {
                MatrixMulti333(tmp[0], pIp->csAttCoreData_Cbo_ESG[0], pIp->csOrbData_coi[0]);
                C2Q(pIp->csAttCoreData_q_ESG, tmp[0]);
                Qdiv(pIp->csAttCoreData_qbt, pIp->csAttCoreData_qri, pIp->csAttCoreData_q_ESG);

                for (i = 0; i < 3; i++)
                {
                    wbt[i] = pIp->csAttCoreData_w_ESG[i] - pIp->csAttCoreData_wri[i];
                }
            }

            if (pIp->csCtrlerOtherPara_FP_Qctrl[WorkMode] == 1)
            {
                for (i=0; i<3; i++)
                {
                    pIp->csAttCoreData_A_c[i] = 2.0 * Asinx(pIp->csAttCoreData_qbt[i]);
                    pIp->csAttCoreData_Rate_c[i] = wbt[i];
                }
            }
            else    /* 采用欧拉角进行误差计算 */
            {
                    pIp->csAttCoreData_A_c[0] = ModPNHP((pIp->csAttCoreData_A_Clp[0] - pIp->csMnvData_A_Ref[0]), 3.141592653589793 ); // PI 3.141592653589793 
                    pIp->csAttCoreData_A_c[1] = ModPNHP((pIp->csAttCoreData_A_Clp[1] - pIp->csMnvData_A_Ref[1]), 3.141592653589793 );
                    pIp->csAttCoreData_A_c[2] = ModPNHP((pIp->csAttCoreData_A_Clp[2] - pIp->csMnvData_A_Ref[2]), 3.141592653589793 );

                    pIp->csAttCoreData_Rate_c[0] = pIp->csAttCoreData_Rate_Clp[0] - pIp->csMnvData_dA_Ref[0];
                    pIp->csAttCoreData_Rate_c[1] = pIp->csAttCoreData_Rate_Clp[1] - pIp->csMnvData_dA_Ref[1];
                    pIp->csAttCoreData_Rate_c[2] = pIp->csAttCoreData_Rate_Clp[2] - pIp->csMnvData_dA_Ref[2];
            }

        }

    }

    return;
}


void CS_Angle2CX_temp2(void *p)
{
    CS_Ctrl_Att_Rate *pIp = (CS_Ctrl_Att_Rate*)p;

    switch(pIp->csAttPara_Seq_AttD[pIp->m_WorkMode])
    {
    case 123:
        Angle2C123(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 132:
        Angle2C132(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 213:
        Angle2C213(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 231:
        Angle2C231(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 312:
        Angle2C312(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 321:
        Angle2C321(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    default:
        Angle2C321(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    }

    return;
}