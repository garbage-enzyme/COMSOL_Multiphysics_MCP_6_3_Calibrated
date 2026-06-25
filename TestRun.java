import java.io.*;

public class TestRun {
    public static void main(String[] args) {
        try {
            PrintStream ps = new PrintStream("C:\\Users\\nguye\\comsol_multiphysics_mcp\\testrun.log");
            ps.println("Hello from TestRun.main()");
            ps.close();
        } catch (Exception e) { }
    }
}
