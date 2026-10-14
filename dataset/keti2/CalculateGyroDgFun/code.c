#include "code.h"

extern void MatrixMulti(float32 *, const float32 *, const float32 *, unint32, unint32, unint32);

void CalculateGyroDgFun(void *p)
{
    CalculateGyroDg *pIp = (CalculateGyroDg*)p;
 	unint08 j ;									
	unint08 k ;									
	float32 tmpwa[5] ;	
	
	for (j = 0 ; j < 5 ; j++ )	                            /* 给临时数组赋值 */
	{
	     tmpwa[j] = 0 ; 									/* 赋值为0，使用时修改 */
    }
	for ( j=0 ; j<pIp->JoinTotal ; j++ )
	{
		k = pIp->SignFlag[j] ;							/* 所有参加诊断陀螺的序号 */								
		tmpwa[j] = pIp->wa[k] ;						/* 取对应序号的模拟量测量值 */				
	}                                                   	
	                                                    	
	if ( pIp->JoinTotal >= 3 )							/* 若大于三个陀螺工作可定姿 */
	{                                                                               		
		                                                    /* 算角速度 */	                        		
		MatrixMulti(&pIp->W[0], pIp->Rtemp, &tmpwa[0], 3, 5, 1) ;										
                                                                                    		
	}                                                                               		
	else                                                                            		
	{                                                                               		
		pIp->W[0] = 0.0f ;								/* 参加定姿的陀螺太少 */						
		pIp->W[1] = 0.0f ;									
		pIp->W[2] = 0.0f ;									
	}
    return;
}
