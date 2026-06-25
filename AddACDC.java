import com.comsol.model.*;
import com.comsol.model.util.*;
import java.io.*;

public class AddACDC {
    public static Model run() {
        try {
            String modelPath = "C:\\Users\\nguye\\comsol_multiphysics_mcp\\comsol_models\\2D_Coils\\2D_Coils_Complete.mph";
            String outputPath = "C:\\Users\\nguye\\comsol_multiphysics_mcp\\comsol_models\\2D_Coils\\2D_Coils_ACDC.mph";
            
            Model model = ModelUtil.load("model", modelPath);
            
            model.component("comp1").physics().create("mf", "InductionCurrents");
            
            model.component("comp1").physics("mf").create("mfi1", "MultiTurnCoil", 1);
            model.component("comp1").physics("mf").feature("mfi1").set("Icoil", "1[A]");
            model.component("comp1").physics("mf").feature("mfi1").selection().set(new int[]{1});
            
            model.component("comp1").physics("mf").create("mfi2", "MultiTurnCoil", 2);
            model.component("comp1").physics("mf").feature("mfi2").set("Icoil", "-1[A]");
            model.component("comp1").physics("mf").feature("mfi2").selection().set(new int[]{2});
            
            model.save(outputPath);
            
            PrintStream ps = new PrintStream(new FileOutputStream("C:\\Users\\nguye\\comsol_multiphysics_mcp\\addacdc_ok.log"));
            ps.println("SUCCESS: Model saved to " + outputPath);
            ps.close();
            
            return model;
        } catch (Exception e) {
            try {
                PrintStream ps = new PrintStream(new FileOutputStream("C:\\Users\\nguye\\comsol_multiphysics_mcp\\addacdc_err.log"));
                ps.println("ERROR: " + e.getMessage());
                e.printStackTrace(ps);
                ps.close();
            } catch (Exception e2) { }
            return null;
        }
    }
    
    public static void main(String[] args) {
        run();
    }
}
