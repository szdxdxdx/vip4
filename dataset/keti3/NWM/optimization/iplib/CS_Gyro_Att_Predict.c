#include "NWM.h"
#include "CS_Gyro_Att_Predict.h"

void Euler_Estimate(void *p);

void    CS_Gyro_Att_PredictFun(void *p)
{
    CS_Gyro_Att_Predict *pIp = (CS_Gyro_Att_Predict*)p;

	unint32 i;

	/* (1) 惯性角速度计算 */
	for (i = 0; i < 3; i++)
	{
		w_ESG[i] = (deltG[i] / Tc - (D0_ESCorr[i] + De_ESCorr[i]) / 3600.0);

		w_ESG[i] = LimitDouble(w_ESG[i], Mlfw);
	}

	/* (2) $@调用《三轴欧拉姿态角预估算法产品规范》*/
	/* void Euler_Estimate(float64 *pAngle, float64 *pRate, float64 *wbo,float64 *pwbi, float64 *w0I, unint32 seq, float64 dta)
	输入/出:A_ESG, 输出:Rate_ESG, 输入:wbo_ESG, 输入:w_ESG, 输入:woi,输入:seq, 输入:DeltaT
	*/
	Euler_Estimate(pIp);

	/* (3) */
	/* 角度限幅 */
	for (i = 0; i < 3; i++)
	{
		Atti_ESG[i] = ModPNHP(Atti_ESG[i], PI);
	}

	/* ijkHex(16进制整数),必须是1,2,3三个数的组合
	123,表示1-2-3转序
	312,表示3-1-2转序
	依次类推...
	*/
	// CS_Angle2C(Cbo_ESG[0], Atti_ESG, Seq_AttD[WorkMode]);
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

	/* 角度限幅 */
	for (i = 0; i < 3; i++)
	{
		Atti_ESG[i] = LimitDouble(Atti_ESG[i],MlfA_ESG[i][WorkMode]);
	}

	return;
}

void Euler_Estimate(void *p)
{
	CS_Gyro_Att_Predict *pIp = (CS_Gyro_Att_Predict*)p;

    float64 cboo[3][3];
    float64 tmat[3];
    siint32 ret;    /* 返回值 */
    float64 tmpatt[3];    /* 增加除０保护 */

    // CS_Angle2C(cboo[0], pIp->pAngle, pIp->seq);  /* Cbo = DCM(ang,seq) */
    switch(Seq_AttD[WorkMode])
    {
    case 123:
        Angle2C123(&cboo[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 132:
        Angle2C132(&cboo[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 213:
        Angle2C213(&cboo[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 231:
        Angle2C231(&cboo[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 312:
        Angle2C312(&cboo[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    case 321:
        Angle2C321(&cboo[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    default:
        Angle2C321(&cboo[0][0], Atti_ESG[0], Atti_ESG[1], Atti_ESG[2]);
        break;
    }
    MatrixMulti(tmat, cboo[0], &woi[0], 3, 3, 1);

    wbo_ESG[0] = w_ESG[0] - tmat[0];
    wbo_ESG[1] = w_ESG[1] - tmat[1];
    wbo_ESG[2] = w_ESG[2] - tmat[2];

    /* w2dAngle(pRate, pIp->pAngle, wbo, (siint32)seq); 转序seq改成十进制了，改调下面这个 */
    // CS_w2dAngleDec(pIp->pRate, pIp->pAngle, pIp->wbo, (siint32)pIp->seq);

    tmpatt[0] = Atti_ESG[0];
    tmpatt[1] = Atti_ESG[1];
    tmpatt[2] = Atti_ESG[2];

    switch ((siint32)Seq_AttD[WorkMode])
    {
    case 123:
        if(Fabsx(Cosx(tmpatt[1])) < 1.0e-7)
        {
            tmpatt[1] = tmpatt[1] + 0.001;
        }
        w2dAngle123(dAtti_ESG, tmpatt, wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 132:
        if(Fabsx(Cosx(tmpatt[2])) < 1.0e-7)
        {
            tmpatt[2] = tmpatt[2] + 0.001;
        }
        w2dAngle132(dAtti_ESG, tmpatt, wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 213:
        if(Fabsx(Cosx(tmpatt[0])) < 1.0e-7)
        {
            tmpatt[0] = tmpatt[0] + 0.001;
        }
        w2dAngle213(dAtti_ESG, tmpatt, wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 231:
        if(Fabsx(Cosx(tmpatt[2])) < 1.0e-7)
        {
            tmpatt[2] = tmpatt[2] + 0.001;
        }
        w2dAngle231(dAtti_ESG, tmpatt, wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 321:
        if(Fabsx(Cosx(tmpatt[1])) < 1.0e-7)
        {
            tmpatt[1] = tmpatt[1] + 0.001;
        }
        w2dAngle321(dAtti_ESG, tmpatt, wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 312:
        if(Fabsx(Cosx(tmpatt[0])) < 1.0e-7)
        {
            tmpatt[0] = tmpatt[0] + 0.001;
        }
        w2dAngle312(dAtti_ESG, tmpatt, wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    default:

        /* 角速率清零 */
        dAtti_ESG[0] = 0.0;
        dAtti_ESG[1] = 0.0;
        dAtti_ESG[2] = 0.0;

        ret = -1;                         /* 转序无效，计算失败 */
        break;
    }

    Atti_ESG[0] = Atti_ESG[0]+dAtti_ESG[0]*Tc;
    Atti_ESG[1] = Atti_ESG[1]+dAtti_ESG[1]*Tc;
    Atti_ESG[2] = Atti_ESG[2]+dAtti_ESG[2]*Tc;

    return;
}