#include "NWM.h"
#include "CS_Ctrl_Att_Rate.h"

void CS_Angle2CX_temp2(void *p);

void CS_Ctrl_Att_RateFun(void *p) 
{
    CS_Ctrl_Att_Rate *pIp = (CS_Ctrl_Att_Rate*)p;
    float64 wbt[3];
    float64 tmp[3][3];
    unint32 i,j;
    unint32 WorkMode__ip_snap = WorkMode;

    /* (1) 全捕姿态控制量赋值 */
    if (FS_ModeProc[WorkMode__ip_snap] == 2)
    {
        for (i=0; i<3; i++)
        {
            Atti_Clp[i]    = Atti_AAM[i];   /* 遥测使用  */
            dAtti_Clp[i] = dAtti_AAM[i];  /* 角速度控制量偏差 */
            wbo_Clp[i]  = w_AAM[i];   /* 实际星体搜索角速度 */

            Atti_C[i]    = Atti_AAM[i];
            Rate_c[i] = dAtti_AAM[i];
        }
    }
    else
    {
    #if 1 //_INCLUDE_ANT_
        /* (2) 历史值赋值 用于机动过程中天线转角外推 */
        if ((ANTGr_LmtH_Num_dw > 0) && (ANTGr_LmtH_Num_dw <= 20))  /* 防越界保护  MAX_LMTH_NUM_DW 20*/
        {
            for (i=(ANTGr_LmtH_Num_dw-1); i>0; i--)
            {
                pIp->csAttCoreData_wbo_Lst[i][0] = pIp->csAttCoreData_wbo_Lst[i-1][0];
                pIp->csAttCoreData_wbo_Lst[i][1] = pIp->csAttCoreData_wbo_Lst[i-1][1];
                pIp->csAttCoreData_wbo_Lst[i][2] = pIp->csAttCoreData_wbo_Lst[i-1][2];
            }
            pIp->csAttCoreData_wbo_Lst[0][0] = wbo_Clp[0];
            pIp->csAttCoreData_wbo_Lst[0][1] = wbo_Clp[1];
            pIp->csAttCoreData_wbo_Lst[0][2] = wbo_Clp[2];
        }
    #endif
        /* (3) 陀螺关闭情况下的姿态赋值 */
        if (FS_AttD == 3)             /* 星敏无陀螺定姿，陀螺关 */
        {
            for (i=0; i<4; i++)
            {
                q_STG[i] = q_STDyn[i];
            }

            for (i=0; i<3; i++)
            {
                w_STG[i] = w_STDyn[i];
            }

            Atti_ESG[0] = Phi_ES;
            Atti_ESG[1] = theta_ES;
            Atti_ESG[2] = Atti_Ref[2];
        }

        if (FS_AttD == 4)             /* 红外无陀螺定姿，红外关 */
        {
            Atti_ESG[0] = Phi_ES;
            Atti_ESG[1] = theta_ES;
            Atti_ESG[2] = 0.0;

            CS_Angle2CX_temp2(pIp);
        }

        /* (4) 姿态及角速度赋值 */
        /* 红外 + 陀螺 */
        if (FS_AttD == 0)
        {
            for (i=0; i<3; i++)
            {
                Atti_Clp[i]  = Atti_ESG[i];
                dAtti_Clp[i]  = dAtti_ESG[i];
                wbo_Clp[i] = wbo_ESG[i];
                w_Clp[i] = w_ESG[i];

                for (j=0; j<3; j++)
                {
                    Cbo_Clp[i][j] = Cbo_ESG[i][j];
                }
            }
        }

        /* 星敏 + 陀螺定姿 */
        else if (FS_AttD == 1)
        {
            for (i=0; i<3; i++)
            {
                dAtti_Clp[i]  = dAtti_STG[i];
                Atti_Clp[i]  = Atti_STG[i];
                wbo_Clp[i] = wbo_STG[i];
                w_Clp[i] = w_STG[i];

                for (j=0; j<3; j++)
                {
                    Cbo_Clp[i][j] = Cbo_STG[i][j];
                }
            }
        }

        /* 星敏无陀螺定姿 */
        else if ((FS_AttD == 2) || (FS_AttD == 3))
        {
            for (i=0; i<3; i++)
            {
                Atti_Clp[i]  = Atti_STDyn[i];
                dAtti_Clp[i]  = dAtti_STDyn[i];
                wbo_Clp[i] = wbo_STDyn[i];
                w_Clp[i] = w_STDyn[i];

                for (j=0; j<3; j++)
                {
                    Cbo_Clp[i][j] = Cbo_STG[i][j];
                }
            }
        }
        /* 红外无陀螺定姿 */
        else if (FS_AttD == 4)
        {
            for (i=0; i<3; i++)
            {
                wbo_Clp[i] = 0.0;
                for (j=0; j<3; j++)
                {
                    Cbo_Clp[i][j] = Cbo_ESG[i][j];
                }
            }

            MatrixMulti331(w_Clp, Cbo_ESG[0], woi);

            Atti_Clp[0] = Phi_ES;
            Atti_Clp[1] = theta_ES;
            Atti_Clp[2] = 0.0;

            dAtti_Clp[0] = dPhi_ES;
            dAtti_Clp[1] = dtheta_ES;
            dAtti_Clp[2] = 0.0;
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
            pIp->csAttCoreData_A_c_Lst[i] = Atti_C[i];
        }

        pIp->csAttCoreData_angqbt_Lst = Acosx(qbt[3]);

        if (FP_BMC == 1)      /* 偏置动量 */
        {
            for (i=0; i<3; i++)
            {
                Atti_C[i] = Atti_Clp[i];
                Rate_c[i] = dAtti_Clp[i];

                if (i == 2)
                {
                    Atti_C[i] = 0.0;
                    Rate_c[i] = 0.0;
                }
            }
        }
        else        /* 零动量 */
        {
            if (FS_AttD == 1)
            {
                Qdiv(qbt, qri, q_STG);

                for (i=0; i<3; i++)
                {
                    wbt[i] = w_STG[i] - wri[i];
                }
            }
            else if ((FS_AttD == 2) || (FS_AttD == 3))
            {
                Qdiv(qbt, qri, q_STDyn);

                for (i=0; i<3; i++)
                {
                    wbt[i] = w_STDyn[i] - wri[i];
                }
            }
            else    /* csAttPara_FS_AttD == 0 */
            {
                MatrixMulti333(tmp[0], Cbo_ESG[0], coi[0]);
                C2Q(q_ESG, tmp[0]);
                Qdiv(qbt, qri, q_ESG);

                for (i = 0; i < 3; i++)
                {
                    wbt[i] = w_ESG[i] - wri[i];
                }
            }

            if (FP_Qctrl[WorkMode__ip_snap] == 1)
            {
                for (i=0; i<3; i++)
                {
                    Atti_C[i] = 2.0 * Asinx(qbt[i]);
                    Rate_c[i] = wbt[i];
                }
            }
            else    /* 采用欧拉角进行误差计算 */
            {
                    Atti_C[0] = ModPNHP((Atti_Clp[0] - Atti_Ref[0]), 3.141592653589793 ); // PI 3.141592653589793 
                    Atti_C[1] = ModPNHP((Atti_Clp[1] - Atti_Ref[1]), 3.141592653589793 );
                    Atti_C[2] = ModPNHP((Atti_Clp[2] - Atti_Ref[2]), 3.141592653589793 );

                    Rate_c[0] = dAtti_Clp[0] - dAtti_Ref[0];
                    Rate_c[1] = dAtti_Clp[1] - dAtti_Ref[1];
                    Rate_c[2] = dAtti_Clp[2] - dAtti_Ref[2];
            }

        }

    }

    return;
}


void CS_Angle2CX_temp2(void *p)
{
    CS_Ctrl_Att_Rate *pIp = (CS_Ctrl_Att_Rate*)p;

    switch(Seq_AttD[WorkMode])
    {
    case 123:
        Angle2C123(&Cbo_ESG[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 132:
        Angle2C132(&Cbo_ESG[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 213:
        Angle2C213(&Cbo_ESG[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 231:
        Angle2C231(&Cbo_ESG[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 312:
        Angle2C312(&Cbo_ESG[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 321:
        Angle2C321(&Cbo_ESG[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    default:
        Angle2C321(&Cbo_ESG[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    }

    return;
}